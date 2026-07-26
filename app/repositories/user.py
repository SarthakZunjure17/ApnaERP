import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.user import UserCreate, UserUpdate


class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    """
    User Repository handling database operations for the User entity.
    """
    def __init__(self):
        super().__init__(User)

    async def get_by_id(self, db: AsyncSession, id: uuid.UUID) -> Optional[User]:
        """
        Retrieves a user by primary key UUID.
        """
        result = await db.execute(select(User).where(User.id == id))
        return result.scalars().first()

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """
        Retrieves a user by email address (case-insensitive).
        """
        result = await db.execute(select(User).where(func.lower(User.email) == email.lower()))
        return result.scalars().first()

    async def get_by_username(self, db: AsyncSession, username: str) -> Optional[User]:
        """
        Retrieves a user by username (case-insensitive).
        """
        result = await db.execute(select(User).where(func.lower(User.username) == username.lower()))
        return result.scalars().first()

    async def create_user(self, db: AsyncSession, *, obj_in: UserCreate, password_hash: str) -> User:
        """
        Creates and persists a new User record with hashed password.
        """
        db_user = User(
            full_name=obj_in.full_name,
            email=obj_in.email,
            username=obj_in.username,
            password_hash=password_hash,
            is_active=True,
            is_superuser=False,
        )
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return db_user

    async def update_last_login(self, db: AsyncSession, *, user_id: uuid.UUID) -> None:
        """
        Updates the last_login timestamp for a user.
        """
        user = await self.get_by_id(db, user_id)
        if user:
            user.last_login = datetime.now(timezone.utc)
            await db.commit()


user_repository = UserRepository()
