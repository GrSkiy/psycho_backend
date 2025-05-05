from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SQLEnum
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

class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Можно добавить title или first_message_preview
    # title: Mapped[str | None] = mapped_column(String)

    user: Mapped[User] = relationship("User", back_populates="chats")
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="chat", order_by="Message.timestamp")

class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    chat_id: Mapped[int] = mapped_column(Integer, ForeignKey("chats.id"))
    sender: Mapped[SenderType] = mapped_column(SQLEnum(SenderType, name="sendertype", native_enum=False), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    chat: Mapped["Chat"] = relationship("Chat", back_populates="messages") 