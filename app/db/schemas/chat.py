from pydantic import BaseModel
from datetime import datetime
from .enums import SenderType
from typing import List

# --- Chat Schemas ---
class ChatBase(BaseModel):
    user_id: int

class ChatCreate(ChatBase):
    pass

class Chat(ChatBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Новая схема для списка чатов
class ChatInfo(BaseModel):
    id: int
    created_at: datetime
    first_message_text: str | None = None # Текст первого сообщения

    class Config:
        from_attributes = True

# --- Message Schemas ---
class MessageBase(BaseModel):
    text: str
    sender: SenderType

class MessageCreate(MessageBase):
    pass

class Message(MessageBase):
    id: int
    chat_id: int
    timestamp: datetime

    class Config:
        from_attributes = True
