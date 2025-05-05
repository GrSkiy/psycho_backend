from pydantic import BaseModel
from datetime import datetime
from typing import List
from .chat import Chat

# --- User Schemas ---
class UserBase(BaseModel):
    username: str | None = None

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int
    created_at: datetime
    chats: List[Chat] = []

    class Config:
        from_attributes = True
