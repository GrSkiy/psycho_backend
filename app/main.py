from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.database import engine # Нужна фабрика сессий и функция get_db
from sqlalchemy import text
import logging
import warnings

# Импорты ваших модулей
from app.db.seeds.user_seed import seed_initial_user
from app.db.models import Base

# Импортируем WebSocket роутер
from app.api.websockets.chat_ws import router as chat_ws_router

warnings.filterwarnings("ignore", module="sqlalchemy")
logging.getLogger("sqlalchemy").setLevel(logging.CRITICAL)
logging.getLogger("sqlalchemy.engine").propagate = False
logging.getLogger("sqlalchemy.engine").handlers = []

async def init_db():
    print("Инициализация базы данных...")

    try:
        async with engine.begin() as conn:
            query = text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
            result = await conn.execute(query)
            existing_tables = [row[0] for row in result.fetchall()]
            
            if existing_tables:
                print(f"Существующие таблицы: {existing_tables}")
                print("✅ Таблицы уже созданы, пропускаем создание.")
                
                # СБРОС ТАБЛИЦ
                # Раскомментируйте следующие строки, если хотите пересоздать таблицы:
                # await conn.run_sync(lambda conn: Base.metadata.drop_all(conn))
                # await conn.run_sync(lambda conn: Base.metadata.create_all(conn))
                # print("Таблицы пересозданы.")
            else:
                print("🔄 Таблиц не найдено, создаем...")
                await conn.run_sync(lambda conn: Base.metadata.create_all(conn))
                
                # Проверяем созданные таблицы
                result = await conn.execute(query)
                created_tables = [row[0] for row in result.fetchall()]
                print(f"✅ Таблицы созданы: {created_tables}")
            
        print("База данных инициализирована.")
    except Exception as e:
        print(f"Ошибка при инициализации базы данных: {e}")
        raise

# --- Контекстный менеджер для управления жизненным циклом (включая startup) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Инициализация БД при запуске
    await init_db()
    await seed_initial_user()

    yield
    print("Приложение останавливается.")


# Передаем lifespan в приложение FastAPI
app = FastAPI(lifespan=lifespan)

# Подключаем WebSocket роутер
app.include_router(chat_ws_router)


@app.get("/")
async def read_root():
    return {"message": "Hello World"}


# @app.get("/users/{user_id}/chats", response_model=List[ChatInfo])
# async def read_user_chats(
#     user_id: int, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
# ):
#     # В реальном приложении здесь должна быть проверка,
#     # что текущий аутентифицированный пользователь запрашивает свои чаты
#     # или имеет права на просмотр чатов user_id.
#     chats = await crud.get_chats_by_user(db=db, user_id=user_id, skip=skip, limit=limit)
#     # Убираем TODO про добавление превью, так как оно теперь есть
#     return chats

# # Здесь позже можно добавить логику подключения к базе данных 