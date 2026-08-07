from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.integrations import ProviderConfiguration
from app.models.user import User
from app.schemas.integrations import ProviderConfigCreate, ProviderConfigResponse
from app.repositories.integration_repos import ProviderConfigurationRepository

router = APIRouter()


@router.post("", response_model=ProviderConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_provider_config(
    req: ProviderConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = ProviderConfigurationRepository()
    config = ProviderConfiguration(
        provider_type=req.provider_type,
        provider_name=req.provider_name,
        settings_json=req.settings_json,
        is_active=req.is_active,
        is_default=req.is_default,
    )
    return await repo.create(db, obj_in=config)
