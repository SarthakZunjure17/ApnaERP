import uuid
from typing import Callable, AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import PyJWTError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User
from app.repositories.user import user_repository
from app.repositories.rbac import user_role_repository
from app.services.rbac import rbac_service

# OAuth2 Password Bearer scheme for Swagger UI & Authorization header parsing
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(reusable_oauth2),
) -> User:
    """
    Dependency injection provider returning current authenticated user from Bearer JWT.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate authentication credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        sub: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if sub is None or token_type != "access":
            raise credentials_exception
        
        user_id = uuid.UUID(sub)
    except (PyJWTError, ValueError):
        raise credentials_exception

    user = await user_repository.get_by_id(db, id=user_id)
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account.",
        )
        
    return user


async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency injection provider enforcing superuser administrative privileges.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin privileges required for this action.",
        )
    return current_user


def has_permission(permission_code: str) -> Callable:
    """
    Dependency factory verifying that the authenticated user possesses the required permission.
    Superusers or users holding 'admin.full_access' bypass specific code checks.
    """
    async def permission_checker(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if current_user.is_superuser:
            return current_user

        user_perms = await rbac_service.get_user_permission_codes(db, current_user.id)
        
        if "admin.full_access" in user_perms or permission_code in user_perms:
            return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: Missing required '{permission_code}' permission.",
        )

    return permission_checker


def has_role(role_name: str) -> Callable:
    """
    Dependency factory verifying that the authenticated user possesses the required role.
    Superusers bypass specific role checks.
    """
    async def role_checker(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if current_user.is_superuser:
            return current_user

        user_roles = await user_role_repository.get_user_roles(db, user_id=current_user.id)
        role_names = {r.name.lower() for r in user_roles}

        if role_name.lower() in role_names or "super admin" in role_names:
            return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: Missing required '{role_name}' role.",
        )

    return role_checker
