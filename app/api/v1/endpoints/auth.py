from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import MessageResponse, RefreshTokenRequest, Token
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.services.auth import auth_service

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New User",
    description="Registers a new user account with unique email and username.",
)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    User registration endpoint.
    """
    user = await auth_service.register_user(db, user_in=user_in)
    return user


@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="User Login",
    description="Authenticates user credentials and returns JWT Access and Refresh tokens.",
)
async def login(
    user_in: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    JSON login endpoint.
    """
    user = await auth_service.authenticate_user(
        db, username_or_email=user_in.username_or_email, password=user_in.password
    )
    return auth_service.create_user_tokens(user.id)


@router.post(
    "/login/form",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="OAuth2 Compatible Form Login",
    description="OAuth2 Form compatible login for Swagger UI interactive authentication.",
    include_in_schema=False,
)
async def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    OAuth2 form login helper endpoint for Swagger UI Authorize button.
    """
    user = await auth_service.authenticate_user(
        db, username_or_email=form_data.username, password=form_data.password
    )
    return auth_service.create_user_tokens(user.id)


@router.post(
    "/refresh",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Refresh Access Token",
    description="Exchanges a valid JWT Refresh Token for a new Access and Refresh Token pair.",
)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Token refresh endpoint.
    """
    return await auth_service.refresh_access_token(db, refresh_token=request.refresh_token)


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="User Logout",
    description="Logs out current user session.",
)
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Logout endpoint acknowledging user logout.
    """
    await auth_service.logout_user(db, user=current_user)
    return MessageResponse(message=f"Successfully logged out user '{current_user.username}'.")


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current Authenticated User",
    description="Retrieves the user profile for the currently authenticated Bearer token user.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Protected current user profile endpoint.
    """
    return current_user
