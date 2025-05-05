from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, text
from sqlalchemy.orm import aliased

# Обновленные импорты схем
from .schemas.user import UserCreate
from .schemas.chat import ChatInfo, MessageCreate
from . import models

# --- User CRUD ---
async def get_user(db: AsyncSession, user_id: int) -> models.User | None:
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    return result.scalar_one_or_none()

async def get_user_by_username(db: AsyncSession, username: str) -> models.User | None:
    result = await db.execute(select(models.User).where(models.User.username == username))
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, user: UserCreate) -> models.User:
    # В реальном приложении здесь нужно хешировать пароль
    # fake_hashed_password = user.password + "notreallyhashed"
    db_user = models.User(
        username=user.username
        # hashed_password=fake_hashed_password
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def get_or_create_user(db: AsyncSession, user_id: int, username: str | None = None):
    """Вспомогательная функция для получения или создания пользователя."""
    db_user = await get_user(db=db, user_id=user_id)
    if db_user:
        print(f"Пользователь с ID {user_id} уже существует.")
        return db_user
    # Создаем пользователя, если его нет
    # Убедись, что схема UserCreate соответствует
    user_in = UserCreate(username=username or f"user_{user_id}")
    print(f"Создание пользователя с ID {user_id} и username {user_in.username}...")
    new_user = await create_user(db=db, user=user_in)
    # --- ВАЖНО: Установка ID вручную (ОПАСНО В PRODUCTION!) ---
    # Так как ID автоинкрементный, мы не можем просто задать user_id=1 при создании.
    # Для простого сидинга *в разработке* можно сделать так, НО это грязный хак.
    # Либо нужно делать пользователя с ID, который выдаст БД, либо настроить модель
    # так, чтобы ID можно было задавать вручную (убрав автоинкремент для user_id=1).
    # Либо, самый чистый способ - не хардкодить ID=1 в main.py, а получать ID
    # реального пользователя после аутентификации.

    # Пока что, для простоты, будем считать, что ID=1 создастся первым,
    # если база пустая, или будем надеяться, что он уже есть.
    # Более надежный seed лучше делать отдельным скриптом или через Alembic data migration.
    print(f"Пользователь создан с ID {new_user.id}") # Посмотрим, какой ID реально присвоился
    return new_user # Вернем созданного пользователя (ID может быть не 1!)

# --- Chat CRUD ---
async def create_chat(db: AsyncSession, user_id: int) -> models.Chat:
    """Создает новый чат для пользователя."""
    db_chat = models.Chat(user_id=user_id)
    db.add(db_chat)
    await db.commit()
    await db.refresh(db_chat)
    print(f"Создан новый чат с ID: {db_chat.id} для пользователя {user_id}")
    return db_chat

async def get_chat(db: AsyncSession, chat_id: int) -> models.Chat | None:
    """Получает чат по ID."""
    result = await db.execute(select(models.Chat).where(models.Chat.id == chat_id))
    return result.scalar_one_or_none()

async def get_chats_by_user(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100) -> list[ChatInfo]:
    """Получает список чатов для пользователя с текстом первого сообщения."""

    # 1. Подзапрос для нахождения ID первого сообщения в каждом чате пользователя
    first_message_subquery = (
        select(
            models.Message.chat_id,
            func.min(models.Message.timestamp).label("min_timestamp")
        )
        .where(models.Message.chat_id.in_(
            select(models.Chat.id).where(models.Chat.user_id == user_id)
        ))
        .group_by(models.Message.chat_id)
        .subquery("first_message_times")
    )

    # Алиас для таблицы сообщений, чтобы присоединить текст первого сообщения
    FirstMessage = aliased(models.Message)

    # 2. Основной запрос: выбираем чаты и присоединяем текст первого сообщения
    # Используем LEFT JOIN от Chat к подзапросу, чтобы включить чаты без сообщений
    query = (
        select(
            models.Chat.id,
            models.Chat.created_at,
            FirstMessage.text.label("first_message_text")
        )
        .select_from(models.Chat) # Явно указываем основную таблицу
        .outerjoin(first_message_subquery, models.Chat.id == first_message_subquery.c.chat_id)
        .outerjoin( # LEFT JOIN к сообщениям
            FirstMessage,
            (models.Chat.id == FirstMessage.chat_id) &
            (FirstMessage.timestamp == first_message_subquery.c.min_timestamp)
        )
        .where(models.Chat.user_id == user_id)
        .order_by(models.Chat.created_at.desc()) # Сначала новые чаты
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(query)

    # Преобразуем результат в список объектов ChatInfo
    chat_infos_raw = result.mappings().all()

    chat_infos = [ChatInfo(**chat_data) for chat_data in chat_infos_raw]

    return chat_infos

# --- Message CRUD ---
async def create_message(db: AsyncSession, message: MessageCreate, chat_id: int) -> models.Message:
    """Создает сообщение в указанном чате."""
    # Проверка существования чата (опционально, но хорошо для надежности)
    db_chat = await get_chat(db, chat_id)
    if not db_chat:
        raise ValueError(f"Чат с ID {chat_id} не найден.")

    db_message = models.Message(
        **message.model_dump(), # Распаковываем данные из схемы (text, sender)
        chat_id=chat_id
    )
    db.add(db_message)
    await db.commit()
    await db.refresh(db_message)
    return db_message

async def get_messages_by_chat(db: AsyncSession, chat_id: int, skip: int = 0, limit: int = 1000) -> list[models.Message]:
    """Получает сообщения для указанного чата, отсортированные по времени."""
    result = await db.execute(
        select(models.Message)
        .where(models.Message.chat_id == chat_id)
        .order_by(models.Message.timestamp.asc()) # Сначала старые для истории чата
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

# async def get_messages_by_session(db: AsyncSession, session_id: str, skip: int = 0, limit: int = 100) -> list[models.Message]:
#     result = await db.execute(
#         select(models.Message)
#         .where(models.Message.session_id == session_id)
#         .order_by(models.Message.timestamp.asc()) # Сначала старые для истории
#         .offset(skip)
#         .limit(limit)
#     )
#     return result.scalars().all() 