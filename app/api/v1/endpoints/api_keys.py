import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.integrations import (
    ApiKeyCreate,
    ApiKeyCreatedResponse,
    ApiKeyResponse,
)
from app.services.integration_services import ApiKeyService

router = APIRouter()


@router.post("", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    req: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ApiKeyService(db)
    api_key, raw_key = await service.create_api_key(
        name=req.name,
        owner_id=current_user.id,
        scopes=req.scopes,
        expires_in_days=req.expires_in_days,
    )
    return ApiKeyCreatedResponse(
        id=api_key.id,
        name=api_key.name,
        prefix=api_key.prefix,
        raw_api_key=raw_key,
        scopes=api_key.scopes,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
    )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ApiKeyService(db)
    success = await service.revoke_key(key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API Key not found")


@router.post("/{key_id}/rotate", response_model=ApiKeyCreatedResponse)
async def rotate_api_key(
    key_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ApiKeyService(db)
    try:
        new_key, raw_key = await service.rotate_key(key_id)
        return ApiKeyCreatedResponse(
            id=new_key.id,
            name=new_key.name,
            prefix=new_key.prefix,
            raw_api_key=raw_key,
            scopes=new_key.scopes,
            expires_at=new_key.expires_at,
            created_at=new_key.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
