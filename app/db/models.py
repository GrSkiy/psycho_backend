from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SQLEnum, Float
from sqlalchemy.orm import relationship, mapped_column, Mapped
from sqlalchemy.sql import func
from datetime import datetime
from .database import Base
from .schemas.enums import SenderType

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # Пока не добавляем email/пароль, нужна логика регистрации/аутентификации
    # email = Column(String, unique=True, index=True, nullable=False)
    # hashed_password = Column(String, nullable=False)
    username: Mapped[str | None] = mapped_column(String, unique=True, index=True, nullable=True) # Или другой идентификатор
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    chats: Mapped[list["Chat"]] = relationship("Chat", back_populates="user")
    diary_entries: Mapped[list["DiaryEntry"]] = relationship("DiaryEntry", back_populates="user")

class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Можно добавить title или first_message_preview
    # title: Mapped[str | None] = mapped_column(String)

    user: Mapped[User] = relationship("User", back_populates="chats")
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="chat", order_by="Message.timestamp")
    diary_entries: Mapped[list["DiaryEntry"]] = relationship("DiaryEntry", back_populates="related_chat")

class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    chat_id: Mapped[int] = mapped_column(Integer, ForeignKey("chats.id"))
    sender: Mapped[SenderType] = mapped_column(SQLEnum(SenderType, name="sendertype", native_enum=False), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    chat: Mapped["Chat"] = relationship("Chat", back_populates="messages") 

class DiaryEntry(Base):
    __tablename__ = "diary_entries"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    event_type: Mapped[str | None] = mapped_column(String, nullable=True)
    emotion_tags: Mapped[str | None] = mapped_column(String, nullable=True)  # JSON строка с тегами
    importance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    related_chat_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("chats.id"), nullable=True)
    
    # Связи
    user: Mapped["User"] = relationship("User", back_populates="diary_entries")
    related_chat: Mapped["Chat"] = relationship("Chat", back_populates="diary_entries") 