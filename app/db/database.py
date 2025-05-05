import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv
from app.core.config import settings


engine = None

if settings.DATABASE_URL.startswith("postgresql+asyncpg://"): # Простая проверка
    try:
        engine = create_async_engine(settings.DATABASE_URL, echo=True)
    except Exception as e:
        print(f"Ошибка при создании движка SQLAlchemy: {e}")
else:
    print("Ошибка: Не удалось сформировать DATABASE_URL.")


# Создаем фабрику асинхронных сессий только если движок создан
AsyncSessionFactory = None
if engine:
    AsyncSessionFactory = async_sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False, # Важно для асинхронного кода
        class_=AsyncSession
    )

Base = declarative_base()

# Функция для получения сессии БД (Dependency для FastAPI)
async def get_db() -> AsyncSession:
    if AsyncSessionFactory is None:
        raise RuntimeError("Фабрика сессий БД не инициализирована.")
    async with AsyncSessionFactory() as session:
        try:
            yield session
        finally:
            pass # Можно оставить pass или пустой finally
