from typing import List, Dict, Any, Optional
from datetime import datetime

from app.db.repositories.diary_repository import DiaryRepository
from app.db.schemas.diary import DiaryEntryCreate, DiaryEntry
from app.services.llm_service import LLMService
from app.utils.prompt_templates import DIARY_SUMMARIZATION_PROMPT

class DiaryService:
    """Service for managing diary entries."""
    
    def __init__(self, diary_repository: DiaryRepository, llm_service: LLMService):
        self.diary_repository = diary_repository
        self.llm_service = llm_service
    
    async def create_entry(
        self, 
        user_id: int,
        title: str,
        content: str,
        event_type: Optional[str] = None,
        emotion_tags: Optional[List[str]] = None,
        importance_score: Optional[float] = None,
        related_chat_id: Optional[int] = None
    ) -> DiaryEntry:
        """Create a new diary entry."""
        entry = DiaryEntryCreate(
            user_id=user_id,
            title=title,
            content=content,
            event_type=event_type,
            emotion_tags=emotion_tags,
            importance_score=importance_score,
            related_chat_id=related_chat_id
        )
        
        return await self.diary_repository.create_entry(entry)
    
    async def summarize_conversation(
        self, 
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = DIARY_SUMMARIZATION_PROMPT
    ) -> Dict[str, Any]:
        """
        Analyze conversation and create a summary for a diary entry.
        
        Args:
            messages: List of chat messages
            system_prompt: Prompt for LLM summarization
            
        Returns:
            Dictionary with summary info including title and content
        """
        analysis_result = await self.llm_service.analyze_context(
            messages=messages,
            query="Создай суммаризацию этого разговора для дневника. "
                  "Включи важные детали о событиях, эмоциях и инсайтах."
        )
        
        return {
            "title": analysis_result.get("diary_entry_title", "Запись в дневнике"),
            "content": analysis_result.get("diary_entry_content", ""),
            "event_type": analysis_result.get("event_type"),
            "emotion_tags": analysis_result.get("emotions", []),
            "importance_score": analysis_result.get("importance_score", 5.0)
        }
    
    async def get_user_entries(
        self, user_id: int, skip: int = 0, limit: int = 50
    ) -> List[DiaryEntry]:
        """Get diary entries for a user."""
        return await self.diary_repository.get_user_entries(
            user_id=user_id, skip=skip, limit=limit
        )
