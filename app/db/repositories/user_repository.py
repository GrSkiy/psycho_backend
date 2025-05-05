"""User repository."""
from typing import Optional
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.base import BaseRepository
from app.db.models import User
from app.db.schemas.user import UserCreate


class UserRepository(BaseRepository[User]):
    """Repository for User entity."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, User)
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        query = select(self.model).where(self.model.username == username)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def create_user(self, user_in: UserCreate) -> User:
        """Create a new user."""
        user_data = user_in.model_dump()
        return await self.create(obj_in=user_data)
    
    async def get_or_create_user(self, user_id: int, username: str = None) -> User:
        """Get user by ID or create if not exists."""
        user = await self.get_by_id(user_id)
        if user:
            print(f"✅ Пользователь с ID {user_id} уже существует.")
            return user
        
        
        # Create user if not exists
        user_data = {
            "username": username or f"user_{user_id}"
        }

        print(f"🔄 Создание пользователя с ID {user_id} и username {user_data['username']}...")
        return await self.create(obj_in=user_data) 
    

    