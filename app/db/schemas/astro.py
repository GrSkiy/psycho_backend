from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

# Здесь будут классы схем для астрологии
# Пример:
"""
class HoroscopeBase(BaseModel):
    zodiac_sign: str
    date: datetime
    prediction: str

class HoroscopeCreate(HoroscopeBase):
    pass

class Horoscope(HoroscopeBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
"""
