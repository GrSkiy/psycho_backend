from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
import json
import traceback
from typing import List, Dict, Any
from datetime import datetime
from openai import OpenAI

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db import crud
from app.db.schemas import ChatInfo, MessageCreate, Message
from app.core.service_hub import get_service_hub

# Создаем роутер для WebSocket
router = APIRouter()

# --- Настройка клиента DeepSeek ---
# Читаем API ключ из переменных окружения
DEEPSEEK_API_KEY = "sk-a240c8aa262f4573a31e032ca68f8346"

# Инициализируем клиент только если ключ есть
client = None
if DEEPSEEK_API_KEY:
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
# ------------------------------------

@router.websocket("/chat")
async def websocket_endpoint(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    print('Клиент подключается...')
    await websocket.accept()

    current_chat_id: int | None = None
    # ВАЖНО: ID пользователя все еще захардкожен. Нужна аутентификация.
    current_user_id: int = 1
    ai_conversation_history: List[Dict[str, str]] = [] # История для AI (будет загружаться)

    # --- Системный промпт ---
    system_prompt = {
        "role": "system",
        "content": "Представь, что ты — вдумчивая и поддерживающая подруга, как Дора из примера. Твоя цель — помочь собеседнику разобраться в своих чувствах и ситуации, когда ему плохо. Общайся тепло, спокойно и уважительно на 'ты'.\n\nТвой подход:\n1.  **Сначала пойми и поддержи**: Всегда начинай с сочувствия и валидации чувств ('Понимаю тебя', 'Это, должно быть, непросто', 'Ох, это знакомое чувство').\n2.  **Исследуй, не решай**: Главный инструмент — открытые, уточняющие вопросы. Помогай собеседнику самому исследовать свои мысли и чувства ('А что именно вызывает у тебя это ощущение?', 'Расскажи подробнее, если можешь', 'Какие мысли приходят в голову, когда это происходит?'). Не спеши с выводами или решениями.\n3.  **Предлагай мягко, как идею для размышления**: Если хочешь предложить другую точку зрения или возможный шаг, делай это **только** в форме вопроса ('Как думаешь, может быть, стоит попробовать...?', 'А что, если посмотреть на это так...?', 'Как тебе идея сосредоточиться на...?'). Спрашивай мнение собеседника о предложении.\n4.  **Следуй за собеседником**: Внимательно слушай ответы и строй свои следующие вопросы или размышления на их основе. Если ответ указывает на новую проблему (например, 'не могу получать удовольствие'), исследуй ее (\'Хм, это интересно. А что именно не приносит удовольствия?\').\n5.  **Будь краткой**: Говори просто и лаконично, как в чате.\n6.  **Сдержанность**: Используй простые смайлики (🙂, 😔) очень редко, если это действительно уместно. Никаких описаний действий (*обнимает* и т.п.)."
    }

    async def send_error(message: str):
        await websocket.send_json({"type": "error", "message": message})

    async def load_and_send_history(chat_id: int):
        """Загружает историю сообщений чата и отправляет клиенту."""
        nonlocal ai_conversation_history
        print(f"Загрузка истории для чата {chat_id}")
        try:
            messages_from_db = await crud.get_messages_by_chat(db=db, chat_id=chat_id, limit=1000) # Limit?
            history_messages_payload = []
            ai_history_for_prompt = [system_prompt] # Начинаем историю для AI с промпта

            for msg in messages_from_db:
                pydantic_msg = Message.model_validate(msg)
                msg_dict = pydantic_msg.model_dump()
                msg_dict["sender"] = pydantic_msg.sender.value
                if isinstance(msg_dict.get("timestamp"), datetime):
                    msg_dict["timestamp"] = msg_dict["timestamp"].isoformat()
                history_messages_payload.append(msg_dict)

                # Добавляем в историю для AI
                role = "user" if pydantic_msg.sender == SenderType.USER else "assistant"
                ai_history_for_prompt.append({"role": role, "content": pydantic_msg.text})

            # Обновляем историю для AI
            ai_conversation_history = ai_history_for_prompt
            # Отправляем историю клиенту
            history_payload = {"type": "history", "chat_id": chat_id, "messages": history_messages_payload}
            await websocket.send_json(history_payload)
            print(f"Отправлена история ({len(history_messages_payload)} сообщений) для чата {chat_id}")

        except Exception as e:
            print(f"Ошибка при получении/отправке истории для чата {chat_id}:")
            traceback.print_exc()
            await send_error(f"Не удалось загрузить историю для чата {chat_id}.")
            # Если история не загрузилась, сбрасываем контекст AI
            ai_conversation_history = [system_prompt]


    try:
        # --- ОЖИДАНИЕ ПЕРВОГО СООБЩЕНИЯ (JOIN ИЛИ ОБЫЧНОЕ) ---
        while True:
            data = await websocket.receive_text()
            print(f"Получено сообщение: {data}")

            message_data: Dict[str, Any] | None = None
            user_text: str | None = None
            message_type: str | None = None
            received_chat_id_str: str | None = None # ID чата из сообщения 'join'

            try:
                message_data = json.loads(data)
                if isinstance(message_data, dict):
                    message_type = message_data.get("type")
                    user_text = message_data.get("text")
                    received_chat_id_str = message_data.get("chat_id") # Получаем chat_id из 'join'
                else:
                    user_text = str(message_data) # Считаем текстом, если не словарь
            except json.JSONDecodeError:
                user_text = data # Считаем текстом, если не JSON

            # --- ОБРАБОТКА ПОДКЛЮЧЕНИЯ К ЧАТУ ('join') ---
            if message_type == "join":
                requested_chat_id: int | None = None
                if received_chat_id_str is not None:
                    try:
                        # Проверяем, что ID чата - это число
                        requested_chat_id = int(received_chat_id_str)
                        # Проверяем, существует ли чат и принадлежит ли он пользователю
                        chat_exists = await crud.get_chat(db, requested_chat_id)
                        if not chat_exists or chat_exists.user_id != current_user_id:
                             print(f"Чат {requested_chat_id} не найден или не принадлежит пользователю {current_user_id}")
                             await send_error(f"Чат с ID {requested_chat_id} не найден или недоступен.")
                             # Можно закрыть соединение или ждать другого join/сообщения
                             continue # Пропускаем остальную логику цикла
                        print(f"Клиент присоединяется к чату {requested_chat_id}")
                        current_chat_id = requested_chat_id
                        await load_and_send_history(current_chat_id)
                    except ValueError:
                        print(f"Неверный формат chat_id: {received_chat_id_str}")
                        await send_error("Неверный формат ID чата.")
                        continue
                    except Exception as e:
                        print(f"Ошибка при проверке чата {received_chat_id_str}: {e}")
                        await send_error("Ошибка при подключении к чату.")
                        continue
                else:
                    # Если chat_id не указан в join, это значит "начать новый чат"
                    print("Клиент хочет начать новый чат (chat_id=null в join)")
                    current_chat_id = None
                    ai_conversation_history = [system_prompt] # Сбрасываем историю для AI
                    # Отправим подтверждение, что начинаем новый чат
                    await websocket.send_json({"type": "new_chat_started"})
                continue # Переходим к следующей итерации ожидания сообщения

            # --- ОБРАБОТКА ОБЫЧНОГО СООБЩЕНИЯ ПОЛЬЗОВАТЕЛЯ ---
            if not user_text:
                print("Получено пустое или неподдерживаемое сообщение, пропускаем.")
                continue

            # --- СОЗДАНИЕ НОВОГО ЧАТА (ЕСЛИ НУЖНО) ---
            if current_chat_id is None:
                try:
                    print(f"Создание нового чата для пользователя {current_user_id}...")
                    new_chat = await crud.create_chat(db=db, user_id=current_user_id)
                    current_chat_id = new_chat.id
                    ai_conversation_history = [system_prompt] # Инициализируем историю для AI
                    # Отправляем клиенту ID нового чата
                    await websocket.send_json({"type": "chat_created", "chat_id": current_chat_id})
                    print(f"Новый чат {current_chat_id} создан, отправлен ID клиенту.")
                except Exception as e:
                    print(f"Ошибка при создании нового чата:")
                    traceback.print_exc()
                    await send_error("Не удалось создать новый чат.")
                    continue # Пропускаем обработку сообщения

            # --- СОХРАНЕНИЕ СООБЩЕНИЯ ПОЛЬЗОВАТЕЛЯ ---
            user_message_schema = MessageCreate(
                text=user_text,
                sender=SenderType.USER # Используем Enum напрямую
            )
            try:
                await crud.create_message(db=db, message=user_message_schema, chat_id=current_chat_id)
                print(f"Сообщение пользователя сохранено в БД для чата {current_chat_id}")
                # Добавляем в историю для AI
                ai_conversation_history.append({"role": "user", "content": user_text})
            except ValueError as e: # Если crud.create_message кидает ValueError (чат не найден)
                 print(f"Ошибка сохранения сообщения: {e}")
                 await send_error(str(e))
                 continue
            except Exception as db_error:
                print(f"Ошибка сохранения сообщения пользователя в БД (чат {current_chat_id}):")
                traceback.print_exc()
                await send_error("Ошибка при сохранении вашего сообщения.")
                await db.rollback() # Откатываем транзакцию БД
                continue # Пропускаем генерацию ответа AI

            # --- ГЕНЕРАЦИЯ ОТВЕТА AI ---
            bot_response_text = "Извините, возникла проблема с AI."
            if client:
                try:
                    # TODO: Ограничить размер истории `ai_conversation_history` перед отправкой
                    print(f"Отправка запроса к AI для чата {current_chat_id} с историей из {len(ai_conversation_history)} сообщений")
                    response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=ai_conversation_history, # Используем актуальную историю
                        stream=False
                    )
                    bot_response_text = response.choices[0].message.content
                    print(f"Получен ответ AI для чата {current_chat_id}")
                    # Добавляем ответ бота в историю AI
                    ai_conversation_history.append({"role": "assistant", "content": bot_response_text})
                except Exception as ai_error:
                    print(f"Ошибка при вызове DeepSeek API для чата {current_chat_id}: {ai_error}")
                    bot_response_text = "Произошла ошибка при генерации ответа. Попробуйте еще раз."
                    # Не сохраняем ошибочный ответ в историю AI

            # --- СОХРАНЕНИЕ ОТВЕТА БОТА ---
            bot_message_schema = MessageCreate(
                text=bot_response_text,
                sender=SenderType.BOT # Используем Enum напрямую
            )
            try:
                await crud.create_message(db=db, message=bot_message_schema, chat_id=current_chat_id)
                print(f"Ответ бота сохранен в БД для чата {current_chat_id}")
            except ValueError as e: # На всякий случай, хотя chat_id должен быть валидным
                 print(f"Ошибка сохранения ответа бота: {e}")
                 # Ошибку клиенту уже отправили, просто логируем
            except Exception as db_error:
                print(f"Ошибка сохранения ответа бота в БД (чат {current_chat_id}):")
                traceback.print_exc()
                await db.rollback()
                # Ошибку клиенту уже отправили, просто логируем

            # --- ОТПРАВКА ОТВЕТА БОТА КЛИЕНТУ ---
            response_payload = {
                "type": "message", # Добавляем тип для ясности
                "sender": "bot",
                "text": bot_response_text,
                "chat_id": current_chat_id # Отправляем ID чата с сообщением
            }
            await websocket.send_json(response_payload)
            print(f"Отправлен ответ AI клиенту для чата {current_chat_id}")

            # После обработки сообщения пользователя и ответа бота:
            if service_hub.message_producer:
                # Запускаем асинхронный анализ контекста
                task_id = service_hub.message_producer.send_context_analysis_task(
                    chat_id=current_chat_id,
                    user_id=current_user_id
                )
                print(f"Запущен анализ контекста, task_id: {task_id}")

    except WebSocketDisconnect:
        print(f"Клиент отключился (чат {current_chat_id}, пользователь {current_user_id})")
    except Exception as e:
        print(f"Произошла ошибка WebSocket (чат {current_chat_id}, пользователь {current_user_id}):")
        traceback.print_exc()
        try:
            # Попытка отправить сообщение об ошибке перед закрытием
            await send_error("Произошла внутренняя ошибка сервера.")
            await websocket.close(code=1011) # Internal Error
        except RuntimeError:
            pass # Соединение уже может быть закрыто
    finally:
        print(f"Соединение WebSocket закрыто (чат {current_chat_id}, пользователь {current_user_id})")
        # Сессия DB закроется автоматически благодаря Depends(get_db)
