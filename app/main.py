from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
import json
import os # Для чтения переменных окружения
from openai import OpenAI # Импортируем OpenAI SDK
from sqlalchemy.ext.asyncio import AsyncSession # Импорт
from contextlib import asynccontextmanager
from db.database import AsyncSessionFactory, get_db # Нужна фабрика сессий и функция get_db
import traceback # Добавить импорт в начало файла
from sqlalchemy.exc import IntegrityError
from typing import List, Dict, Any # Добавить для типизации
from datetime import datetime

# Импорты ваших модулей
from db import crud, schemas, models # Импорт CRUD, схем и моделей

# --- Настройка клиента DeepSeek ---
# Читаем API ключ из переменных окружения
DEEPSEEK_API_KEY = "sk-a240c8aa262f4573a31e032ca68f8346"

# Инициализируем клиент только если ключ есть
client = None
if DEEPSEEK_API_KEY:
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
# ------------------------------------

# --- Функция для создания пользователя при старте ---
async def seed_initial_user():
    if AsyncSessionFactory is None:
        print("Фабрика сессий не инициализирована, пропуск сидинга.")
        return
    print("Проверка/создание начального пользователя...")
    async with AsyncSessionFactory() as session:
        # Пытаемся получить или создать пользователя с ID=1
        # Для примера, username будет 'testuser1'
        # ВНИМАНИЕ: ID=1 может не сработать как ожидается (см. crud.py)

        await crud.get_or_create_user(db=session, user_id=1, username="testuser1")
        # Можно добавить создание других начальных данных здесь
    print("Проверка/создание начального пользователя завершено.")


# --- Контекстный менеджер для управления жизненным циклом (включая startup) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Код перед запуском приложения
    await seed_initial_user()
    yield
    # Код после остановки приложения (если нужен)
    print("Приложение останавливается.")


# Передаем lifespan в приложение FastAPI
app = FastAPI(lifespan=lifespan)


@app.get("/")
async def read_root():
    return {"message": "Hello World"}


# --- Эндпоинт для истории через HTTP (можно оставить или удалить, если используешь только WebSocket) ---
@app.get("/users/{user_id}/messages", response_model=List[schemas.Message])
async def read_user_messages(
    user_id: int, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
):
    messages = await crud.get_messages_by_user(db=db, user_id=user_id, skip=skip, limit=limit)
    return messages
# -------------------------------------------------------------------------------------------


@app.websocket("/chat")
async def websocket_endpoint(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    print('Клиент подключается...')
    await websocket.accept()
    conversation_history = [
        {
            "role": "system",
            "content": "Представь, что ты — вдумчивая и поддерживающая подруга, как Дора из примера. Твоя цель — помочь собеседнику разобраться в своих чувствах и ситуации, когда ему плохо. Общайся тепло, спокойно и уважительно на 'ты'.\n\nТвой подход:\n1.  **Сначала пойми и поддержи**: Всегда начинай с сочувствия и валидации чувств ('Понимаю тебя', 'Это, должно быть, непросто', 'Ох, это знакомое чувство').\n2.  **Исследуй, не решай**: Главный инструмент — открытые, уточняющие вопросы. Помогай собеседнику самому исследовать свои мысли и чувства ('А что именно вызывает у тебя это ощущение?', 'Расскажи подробнее, если можешь', 'Какие мысли приходят в голову, когда это происходит?'). Не спеши с выводами или решениями.\n3.  **Предлагай мягко, как идею для размышления**: Если хочешь предложить другую точку зрения или возможный шаг, делай это **только** в форме вопроса ('Как думаешь, может быть, стоит попробовать...?', 'А что, если посмотреть на это так...?', 'Как тебе идея сосредоточиться на...?'). Спрашивай мнение собеседника о предложении.\n4.  **Следуй за собеседником**: Внимательно слушай ответы и строй свои следующие вопросы или размышления на их основе. Если ответ указывает на новую проблему (например, 'не могу получать удовольствие'), исследуй ее ('Хм, это интересно. А что именно не приносит удовольствия?').\n5.  **Будь краткой**: Говори просто и лаконично, как в чате.\n6.  **Сдержанность**: Используй простые смайлики (🙂, 😔) очень редко, если это действительно уместно. Никаких описаний действий (*обнимает* и т.п.)."
        },
    ]

    current_user_id: int = 1 # ВАЖНО: Пока ID пользователя захардкожен

    try:
        while True:
            data = await websocket.receive_text()
            print(f"Получено сообщение: {data}")

            message_data: Dict[str, Any] | None = None
            user_text: str | None = None
            message_type: str | None = None

            # Пытаемся распарсить JSON
            try:
                message_data = json.loads(data)
                if isinstance(message_data, dict):
                    message_type = message_data.get("type")
                    user_text = message_data.get("text") # Может быть и обычное сообщение в JSON
                else:
                    # Если пришел не словарь (например, просто строка в JSON), считаем текстом
                    user_text = str(message_data)
            except json.JSONDecodeError:
                # Если не JSON, считаем весь текст сообщением пользователя
                user_text = data

            # --- ОБРАБОТКА ЗАПРОСА ИСТОРИИ ---
            if message_type == "get_history":
                print(f"Запрос истории для пользователя {current_user_id}")
                try:
                    messages_from_db: List[models.Message] = await crud.get_messages_by_user(
                        db=db, user_id=current_user_id, limit=1000
                    )

                    history_messages = []
                    for msg in messages_from_db:
                        pydantic_msg = schemas.Message.model_validate(msg)
                        msg_dict = pydantic_msg.model_dump()
                        # Заменяем объект Enum на его строковое значение
                        msg_dict["sender"] = pydantic_msg.sender.value

                        # Явно преобразуем datetime в строку ISO 8601
                        if isinstance(msg_dict.get("timestamp"), datetime):
                            msg_dict["timestamp"] = msg_dict["timestamp"].isoformat()

                        history_messages.append(msg_dict)

                    history_payload = {"type": "history", "messages": history_messages}
                    await websocket.send_json(history_payload)
                    print(f"Отправлена история ({len(history_messages)} сообщений)")
                except Exception as e:
                    print(f"Ошибка при получении/отправке истории:")
                    traceback.print_exc()
                    await websocket.send_json({"type": "error", "message": "Не удалось загрузить историю."})
                continue

            # --- ОБРАБОТКА ОБЫЧНОГО СООБЩЕНИЯ ПОЛЬЗОВАТЕЛЯ ---
            if not user_text:
                print("Получено пустое сообщение, пропускаем.")
                continue # Пропускаем пустые сообщения

            # 1. Сохранить сообщение пользователя в БД
            # Используем schemas.SenderType.USER.value для строки 'USER'
            user_message_data = schemas.MessageCreate(
                text=user_text,
                sender=schemas.SenderType.USER.value, # Передаем строковое значение
                user_id=current_user_id
            )
            try:
                await crud.create_message(db=db, message=user_message_data)
                print("Сообщение пользователя сохранено в БД")
            except IntegrityError as e:
                print(f"Ошибка БД (вероятно, user_id не найден или другое ограничение): {e}")
                await db.rollback()
            except Exception as db_error:
                print(f"Другая ошибка сохранения сообщения пользователя в БД:")
                traceback.print_exc()
                await db.rollback()

            # Добавляем сообщение пользователя в историю для контекста AI
            conversation_history.append({"role": "user", "content": user_text})

            bot_response_text = "Извините, возникла проблема с подключением к AI." # Ответ по умолчанию

            # Вызываем DeepSeek API, если клиент инициализирован
            if client:
                try:
                    response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=conversation_history,
                        stream=False # Пока без стриминга для простоты
                    )
                    bot_response_text = response.choices[0].message.content
                    # Добавляем ответ бота в историю
                    conversation_history.append({"role": "assistant", "content": bot_response_text})
                    # TODO: Ограничить размер истории, чтобы не превышать лимиты токенов
                except Exception as ai_error:
                    print(f"Ошибка при вызове DeepSeek API: {ai_error}")
                    # Можно отправить сообщение об ошибке пользователю
                    bot_response_text = "Произошла ошибка при генерации ответа. Попробуйте еще раз."

            # 2. Сохранить ответ бота в БД
            # Используем schemas.SenderType.BOT.value для строки 'BOT'
            bot_message_data = schemas.MessageCreate(
                text=bot_response_text,
                sender=schemas.SenderType.BOT.value, # Передаем строковое значение
                user_id=current_user_id
            )
            try:
                await crud.create_message(db=db, message=bot_message_data)
                print("Ответ бота сохранен в БД")
            except IntegrityError as e:
                print(f"Ошибка БД (вероятно, user_id не найден или другое ограничение): {e}")
                await db.rollback()
            except Exception as db_error:
                print(f"Другая ошибка сохранения ответа бота в БД:")
                traceback.print_exc()
                await db.rollback()

            # Отправляем ОБЫЧНЫЙ ответ бота клиенту
            response_payload = {"sender": "bot", "text": bot_response_text} # Тип не 'history'
            await websocket.send_json(response_payload)
            print(f"Отправлен ответ AI: {response_payload}")

    except WebSocketDisconnect:
        print("Клиент отключился")
    except Exception as e:
        print(f"Произошла ошибка WebSocket:")
        traceback.print_exc()
        # Попытаться закрыть соединение корректно
        try:
            await websocket.close()
        except RuntimeError:
            pass # Соединение уже может быть закрыто
    finally:
        # Сессия закроется автоматически благодаря 'async with' в get_db
        print("Соединение WebSocket закрыто")

# Здесь позже можно добавить логику подключения к базе данных 