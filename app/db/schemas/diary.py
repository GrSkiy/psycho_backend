from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


class DiaryEntryBase(BaseModel):
    title: str
    content: str
    event_type: Optional[str] = None
    emotion_tags: Optional[List[str]] = None
    importance_score: Optional[float] = None

class DiaryEntryCreate(DiaryEntryBase):
    user_id: int
    related_chat_id: Optional[int] = None

class DiaryEntryUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    event_type: Optional[str] = None
    emotion_tags: Optional[List[str]] = None
    importance_score: Optional[float] = None

class DiaryEntry(DiaryEntryBase):
    id: int
    user_id: int
    created_at: datetime
    related_chat_id: Optional[int] = None

    class Config:
        from_attributes = True
