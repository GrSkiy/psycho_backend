from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

# Здесь будут классы схем для таро
# Пример:
"""
class TarotCardBase(BaseModel):
    name: str
    position: int
    interpretation: str

class TarotReadingBase(BaseModel):
    question: str
    interpretation: str

class TarotReadingCreate(TarotReadingBase):
    user_id: int
    cards: List[TarotCardBase]

class TarotReading(TarotReadingBase):
    id: int
    user_id: int
    created_at: datetime
    cards: List["TarotCard"] = []

    class Config:
        from_attributes = True

class TarotCard(TarotCardBase):
    id: int
    reading_id: int

    class Config:
        from_attributes = True
"""
