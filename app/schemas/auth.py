from typing import Optional
from pydantic import BaseModel, Field


class Token(BaseModel):
    """
    Schema for JWT Token response after successful authentication.
    """
    access_token: str = Field(..., description="JWT Access Token")
    refresh_token: str = Field(..., description="JWT Refresh Token")
    token_type: str = Field("bearer", description="Token type")


class TokenPayload(BaseModel):
    """
    Schema representing decoded JWT token payload.
    """
    sub: Optional[str] = None
    exp: Optional[int] = None
    type: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    """
    Schema for Refresh Token request.
    """
    refresh_token: str = Field(..., description="Valid JWT Refresh Token")


class MessageResponse(BaseModel):
    """
    Generic message response schema.
    """
    message: str = Field(..., description="Response message detail")
