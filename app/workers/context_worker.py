from typing import Dict, Any, List, Optional
import json

from app.workers.celery_app import app
from app.services.llm_service import LLMService
from app.services.diary_service import DiaryService
from app.db.repositories.diary_repository import DiaryRepository
from app.db.repositories.chat_repository import ChatRepository
from app.utils.prompt_templates import CONTEXT_ANALYSIS_PROMPT

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import AsyncSessionFactory

# Функция для получения сессии
async def get_session():
    async with AsyncSessionFactory() as session:
        yield session

@app.task
def analyze_conversation_context(chat_id: int, user_id: int):
    """
    Analyze conversation context and create diary entry if needed.
    
    Args:
        chat_id: ID of the chat
        user_id: ID of the user
    """
    # Инициализация клиента LLM
    from app.core.config import settings
    from openai import OpenAI
    
    client = OpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL
    )
    
    # Получение контекста беседы
    import asyncio
    
    async def process():
        # Получаем сессию базы данных
        session = AsyncSession(bind=AsyncSessionFactory.sync_engine)
        
        # Инициализируем репозитории и сервисы
        chat_repo = ChatRepository(session)
        diary_repo = DiaryRepository(session)
        
        llm_service = LLMService(client)
        diary_service = DiaryService(diary_repo, llm_service)
        
        # Получаем сообщения из чата
        messages = await chat_repo.get_messages_by_chat(chat_id, limit=30)
        
        # Если сообщений нет, не делаем анализ
        if not messages:
            return {"status": "no_messages"}
        
        # Преобразуем сообщения в формат для LLM
        formatted_messages = []
        for msg in messages:
            role = "user" if msg.sender.value == "USER" else "assistant"
            formatted_messages.append({"role": role, "content": msg.text})
        
        # Анализируем контекст
        analysis_result = await llm_service.analyze_context(
            messages=formatted_messages,
            query=CONTEXT_ANALYSIS_PROMPT
        )
        
        # Проверяем, нужно ли создать запись в дневнике
        should_create_diary = analysis_result.get("should_create_diary", False)
        
        if should_create_diary:
            # Создаем запись в дневнике
            diary_entry = await diary_service.create_entry(
                user_id=user_id,
                title=analysis_result.get("diary_entry_title", "Новая запись"),
                content=analysis_result.get("diary_entry_content", ""),
                event_type=analysis_result.get("main_topic"),
                emotion_tags=analysis_result.get("emotions", []),
                importance_score=8.0,  # По умолчанию высокая важность для автосозданных
                related_chat_id=chat_id
            )
            
            return {
                "status": "diary_created",
                "diary_entry_id": diary_entry.id,
                "diary_entry_title": diary_entry.title
            }
        
        return {"status": "no_diary_needed"}
    
    # Запускаем асинхронный код
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(process())
    
    return result
