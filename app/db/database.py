import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла (особенно для Alembic)
load_dotenv()

POSTGRES_USER = os.getenv("POSTGRES_USER", "myuser")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "mypassword")
POSTGRES_DB = os.getenv("POSTGRES_DB", "mydatabase")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5433")



# Асинхронный URL для FastAPI/SQLAlchemy
DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
# Синхронный URL для Alembic (использует psycopg2)
SYNC_DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"


# Проверка, что URL сформирован (хотя с default значениями он будет)
# if not all([POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_HOST, POSTGRES_PORT]):
#     print("Ошибка: Не все переменные окружения для подключения к БД установлены.")
    # exit(1) # Лучше не использовать exit() в модуле

# Создаем асинхронный движок SQLAlchemy
# Убедимся, что DATABASE_URL вообще существует перед созданием движка
engine = None
if DATABASE_URL.startswith("postgresql+asyncpg://"): # Простая проверка
    try:
        engine = create_async_engine(DATABASE_URL, echo=True) # echo=True для отладки SQL запросов
    except Exception as e:
        print(f"Ошибка при создании движка SQLAlchemy: {e}")
        # exit(1) # Лучше обработать ошибку выше по стеку
else:
    print("Ошибка: Не удалось сформировать DATABASE_URL.")
    # exit(1)


# Создаем фабрику асинхронных сессий только если движок создан
AsyncSessionFactory = None
if engine:
    AsyncSessionFactory = async_sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False, # Важно для асинхронного кода
        class_=AsyncSession
    )

# Базовый класс для декларативных моделей
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

# ... остальные функции и переменные остаются без изменений ... 