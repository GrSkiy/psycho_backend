from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from . import models, schemas

# --- User CRUD ---
async def get_user(db: AsyncSession, user_id: int) -> models.User | None:
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    return result.scalar_one_or_none()

async def get_user_by_username(db: AsyncSession, username: str) -> models.User | None:
    result = await db.execute(select(models.User).where(models.User.username == username))
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, user: schemas.UserCreate) -> models.User:
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
    user_in = schemas.UserCreate(username=username or f"user_{user_id}")
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

# --- Message CRUD ---
async def create_message(db: AsyncSession, message: schemas.MessageCreate) -> models.Message:
    db_message = models.Message(
        text=message.text,
        sender=message.sender,
        user_id=message.user_id
        # session_id=message.session_id
    )
    db.add(db_message)
    await db.commit()
    await db.refresh(db_message)
    return db_message

async def get_messages_by_user(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100) -> list[models.Message]:
    result = await db.execute(
        select(models.Message)
        .where(models.Message.user_id == user_id)
        .order_by(models.Message.timestamp.desc()) # Сначала новые
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