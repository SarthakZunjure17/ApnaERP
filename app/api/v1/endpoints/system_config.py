from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.integrations import SystemConfiguration
from app.models.user import User
from app.schemas.integrations import SystemConfigResponse, SystemConfigSetRequest
from app.repositories.integration_repos import SystemConfigurationRepository

router = APIRouter()


@router.post("", response_model=SystemConfigResponse, status_code=status.HTTP_200_OK)
async def set_system_config(
    req: SystemConfigSetRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = SystemConfigurationRepository()
    existing = await repo.get_by_key(db, req.config_key)
    if existing:
        existing.config_value = req.config_value
        existing.value_type = req.value_type
        existing.category = req.category
        existing.is_encrypted = req.is_encrypted
        existing.is_public = req.is_public
        await db.commit()
        await db.refresh(existing)
        return existing
    else:
        new_config = SystemConfiguration(
            config_key=req.config_key,
            config_value=req.config_value,
            value_type=req.value_type,
            category=req.category,
            is_encrypted=req.is_encrypted,
            is_public=req.is_public,
        )
        return await repo.create(db, obj_in=new_config)


@router.get("/{config_key}", response_model=SystemConfigResponse)
async def get_system_config(
    config_key: str,
    db: AsyncSession = Depends(get_db),
):
    repo = SystemConfigurationRepository()
    config = await repo.get_by_key(db, config_key)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration key not found")
    return config
