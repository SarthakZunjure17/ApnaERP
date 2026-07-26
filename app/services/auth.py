import uuid
from typing import Optional
from fastapi import HTTPException, status
from jwt.exceptions import PyJWTError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user import user_repository
from app.schemas.auth import Token
from app.schemas.user import UserCreate
from app.services.base import BaseService
from app.utils.audit import log_audit


class AuthService(BaseService[user_repository.__class__]):
    """
    Service layer handling User authentication, registration, password validation, and token issuing.
    """
    def __init__(self):
        super().__init__(user_repository)

    async def register_user(self, db: AsyncSession, user_in: UserCreate) -> User:
        """
        Registers a new user after verifying unique email and username.
        """
        existing_email = await self.repository.get_by_email(db, user_in.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists.",
            )

        existing_username = await self.repository.get_by_username(db, user_in.username)
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this username already exists.",
            )

        hashed_pwd = hash_password(user_in.password)
        user = await self.repository.create_user(db, obj_in=user_in, password_hash=hashed_pwd)

        # Record audit log
        await log_audit(
            db,
            action="USER_REGISTER",
            entity_type="User",
            entity_id=user.id,
            user_id=user.id,
            username=user.username,
            new_data={"email": user.email, "username": user.username, "full_name": user.full_name},
            status_code=201,
        )

        return user

    async def authenticate_user(
        self, db: AsyncSession, username_or_email: str, password: str
    ) -> User:
        """
        Authenticates user credentials by username or email.
        """
        user = await self.repository.get_by_email(db, username_or_email)
        if not user:
            user = await self.repository.get_by_username(db, username_or_email)

        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username/email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user account.",
            )

        await self.repository.update_last_login(db, user_id=user.id)

        # Record audit log
        await log_audit(
            db,
            action="LOGIN",
            entity_type="User",
            entity_id=user.id,
            user_id=user.id,
            username=user.username,
            status_code=200,
        )

        return user

    def create_user_tokens(self, user_id: uuid.UUID) -> Token:
        """
        Generates access and refresh tokens for an authenticated user ID.
        """
        access_token = create_access_token(subject=user_id)
        refresh_token = create_refresh_token(subject=user_id)
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )

    async def refresh_access_token(self, db: AsyncSession, refresh_token: str) -> Token:
        """
        Validates refresh token and issues a new access token pair.
        """
        try:
            payload = decode_token(refresh_token)
            token_type = payload.get("type")
            sub = payload.get("sub")

            if token_type != "refresh" or not sub:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token type.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            user_id = uuid.UUID(sub)
        except (PyJWTError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = await self.repository.get_by_id(db, user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return self.create_user_tokens(user.id)

    async def logout_user(self, db: AsyncSession, user: User) -> None:
        """
        Logs out user and records LOGOUT audit event.
        """
        await log_audit(
            db,
            action="LOGOUT",
            entity_type="User",
            entity_id=user.id,
            user_id=user.id,
            username=user.username,
            status_code=200,
        )


auth_service = AuthService()
