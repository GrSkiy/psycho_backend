from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

# Здесь будут классы схем для дневника
# Пример:
"""
class DiaryEntryBase(BaseModel):
    title: str
    content: str
    mood: str = None

class DiaryEntryCreate(DiaryEntryBase):
    user_id: int

class DiaryEntry(DiaryEntryBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime = None

    class Config:
        from_attributes = True
"""
