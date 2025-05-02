from pydantic import BaseModel
from datetime import datetime
from .enums import SenderType

# --- Message Schemas ---
class MessageBase(BaseModel):
    text: str
    sender: SenderType

class MessageCreate(MessageBase):
    user_id: int | None = None # ID пользователя, если он есть
    # session_id: str | None = None # ID сессии

class Message(MessageBase):
    id: int
    user_id: int | None
    # session_id: str | None
    timestamp: datetime

    class Config:
        from_attributes = True # Раньше было orm_mode = True

# --- User Schemas ---
class UserBase(BaseModel):
    username: str | None = None # Или email, если используешь его
    # email: str

class UserCreate(UserBase):
    # password: str # Пароль передается только при создании
    pass

class User(UserBase):
    id: int
    created_at: datetime
    messages: list[Message] = [] # Показываем сообщения пользователя

    class Config:
        from_attributes = True # Раньше было orm_mode = True 