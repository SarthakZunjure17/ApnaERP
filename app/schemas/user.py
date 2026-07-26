import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """
    Shared User properties across schemas.
    """
    email: EmailStr = Field(..., description="User's email address")
    username: str = Field(..., min_length=3, max_length=50, description="User's unique username")
    full_name: str = Field(..., min_length=1, max_length=255, description="User's full name")


class UserCreate(UserBase):
    """
    Schema for User registration request.
    """
    password: str = Field(..., min_length=8, max_length=128, description="User's password (min 8 characters)")


class UserLogin(BaseModel):
    """
    Schema for User login request. Accepts email or username.
    """
    username_or_email: str = Field(..., description="Registered username or email address")
    password: str = Field(..., description="User password")


class UserUpdate(BaseModel):
    """
    Schema for updating user details.
    """
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = Field(None)
    password: Optional[str] = Field(None, min_length=8, max_length=128)
    is_active: Optional[bool] = Field(None)


class UserResponse(UserBase):
    """
    Schema for User data returned in API responses.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Unique User UUID")
    is_active: bool = Field(..., description="Active status")
    is_superuser: bool = Field(..., description="Superuser status")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Account last update timestamp")
