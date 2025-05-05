"""Service Hub for managing service instances."""
from typing import Dict, Any, Optional
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from openai import OpenAI

from app.db.database import get_db
from app.core.config import settings
from app.db.repositories.user_repository import UserRepository
from app.db.repositories.chat_repository import ChatRepository
from app.db.repositories.diary_repository import DiaryRepository
from app.services.llm_service import LLMService
from app.services.diary_service import DiaryService


class ServiceHub:
    """
    Central component that initializes, stores and provides
    access to all application services.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize ServiceHub with a database session.
        
        Args:
            db: Database session
        """
        self.db = db
        
        # Initialize LLM client
        self.llm_client = self._create_llm_client()
        
        # Initialize repositories (will be implemented later)
        self.repositories = self._init_repositories()
        
        # Initialize services (will be implemented later)
        self.services = self._init_services()
    
    def _create_llm_client(self) -> OpenAI:
        """Create an LLM client."""
        return OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL
        )
    
    def _init_repositories(self) -> Dict[str, Any]:
        """Initialize repositories."""
        return {
            "user": UserRepository(self.db),
            "chat": ChatRepository(self.db),
            "diary": DiaryRepository(self.db),
            # Другие репозитории...
        }
    
    def _init_services(self) -> Dict[str, Any]:
        """Initialize services."""
        # Создаем базовые сервисы
        llm_service = LLMService(self.llm_client)
        
        # Создаем сервисы с зависимостями
        services = {
            "llm": llm_service,
            "diary": DiaryService(
                self.repositories["diary"],
                llm_service
            ),
            # Другие сервисы...
        }
        
        return services

    @property
    def diary_service(self) -> DiaryService:
        return self.services["diary"]


# FastAPI dependency
async def get_service_hub(db: AsyncSession = Depends(get_db)) -> ServiceHub:
    """
    Get a ServiceHub instance as a FastAPI dependency.
    
    Usage:
        @app.get("/endpoint")
        async def endpoint(service_hub: ServiceHub = Depends(get_service_hub)):
            return service_hub.some_service.do_something()
    """
    return ServiceHub(db) 