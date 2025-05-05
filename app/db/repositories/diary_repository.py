from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.db.repositories.base import BaseRepository
from app.db.models import DiaryEntry
from app.db.schemas.diary import DiaryEntryCreate, DiaryEntryUpdate

class DiaryRepository(BaseRepository[DiaryEntry]):
    """Repository for diary entries."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, DiaryEntry)
    
    async def create_entry(self, entry: DiaryEntryCreate) -> DiaryEntry:
        """Create a new diary entry."""
        entry_data = entry.model_dump()
        
        # Преобразуем списки в JSON строки
        if "emotion_tags" in entry_data and entry_data["emotion_tags"] is not None:
            entry_data["emotion_tags"] = json.dumps(entry_data["emotion_tags"])
        
        return await self.create(obj_in=entry_data)
    
    async def get_user_entries(
        self, user_id: int, skip: int = 0, limit: int = 50
    ) -> List[DiaryEntry]:
        """Get diary entries for a user."""
        query = (
            select(DiaryEntry)
            .where(DiaryEntry.user_id == user_id)
            .order_by(DiaryEntry.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_entries_by_type(
        self, user_id: int, event_type: str, skip: int = 0, limit: int = 50
    ) -> List[DiaryEntry]:
        """Get diary entries by event type."""
        query = (
            select(DiaryEntry)
            .where(DiaryEntry.user_id == user_id, DiaryEntry.event_type == event_type)
            .order_by(DiaryEntry.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()
