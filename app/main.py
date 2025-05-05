from db.schemas import ChatInfo, MessageCreate, Message
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
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
from db import crud, models # Импорт CRUD, схем и моделей

# Импортируем WebSocket роутер
from api.websockets.chat_ws import router as chat_ws_router

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

# Подключаем WebSocket роутер
app.include_router(chat_ws_router)


@app.get("/")
async def read_root():
    return {"message": "Hello World"}


@app.get("/users/{user_id}/chats", response_model=List[ChatInfo])
async def read_user_chats(
    user_id: int, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
):
    # В реальном приложении здесь должна быть проверка,
    # что текущий аутентифицированный пользователь запрашивает свои чаты
    # или имеет права на просмотр чатов user_id.
    chats = await crud.get_chats_by_user(db=db, user_id=user_id, skip=skip, limit=limit)
    # Убираем TODO про добавление превью, так как оно теперь есть
    return chats

# Здесь позже можно добавить логику подключения к базе данных 