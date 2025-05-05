"""Chat repository."""
from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, text
from sqlalchemy.orm import selectinload, aliased

from app.db.repositories.base import BaseRepository
from app.db.models import Chat, Message
from app.db.schemas.chat import ChatInfo, MessageCreate
from app.db.schemas.enums import SenderType


class ChatRepository(BaseRepository[Chat]):
    """Repository for Chat entity."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, Chat)
    
    async def create_chat(self, user_id: int) -> Chat:
        """Create a new chat for a user."""
        chat_data = {"user_id": user_id}
        return await self.create(obj_in=chat_data)
    
    async def get_chats_by_user(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[ChatInfo]:
        """Get chats for a user with first message preview."""
        # Subquery to find the first message timestamp in each chat
        first_message_subquery = (
            select(
                Message.chat_id,
                func.min(Message.timestamp).label("min_timestamp")
            )
            .where(Message.chat_id.in_(
                select(Chat.id).where(Chat.user_id == user_id)
            ))
            .group_by(Message.chat_id)
            .subquery("first_message_times")
        )
        
        # Create alias for Message table to join first message text
        FirstMessage = aliased(Message)
        
        # Main query: select chats with first message text
        query = (
            select(
                Chat.id,
                Chat.created_at,
                FirstMessage.text.label("first_message_text")
            )
            .select_from(Chat)
            .outerjoin(
                first_message_subquery, 
                Chat.id == first_message_subquery.c.chat_id
            )
            .outerjoin(
                FirstMessage,
                (Chat.id == FirstMessage.chat_id) & 
                (FirstMessage.timestamp == first_message_subquery.c.min_timestamp)
            )
            .where(Chat.user_id == user_id)
            .order_by(Chat.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        chat_infos_raw = result.mappings().all()
        
        return [ChatInfo(**chat_data) for chat_data in chat_infos_raw]
    
    async def create_message(
        self, message: MessageCreate, chat_id: int
    ) -> Message:
        """Create a message in a chat."""
        # Check if chat exists
        chat = await self.get_by_id(chat_id)
        if not chat:
            raise ValueError(f"Chat with ID {chat_id} not found.")
        
        # Create message
        message_data = message.model_dump()
        message_data["chat_id"] = chat_id
        
        # Direct creation of Message since it's not the primary model of this repo
        db_message = Message(**message_data)
        self.db.add(db_message)
        await self.db.commit()
        await self.db.refresh(db_message)
        
        return db_message
    
    async def get_messages_by_chat(
        self, chat_id: int, skip: int = 0, limit: int = 1000
    ) -> List[Message]:
        """Get messages for a chat."""
        query = (
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(Message.timestamp.asc())
            .offset(skip)
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        return result.scalars().all() 