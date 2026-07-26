from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, has_permission
from app.exceptions.base import ApnaERPException
from app.models.user import User
from app.schemas.hr_configuration import (
    HRConfigurationCreate,
    HRConfigurationResponse,
    HRConfigurationUpdate,
)
from app.services.hr_configuration import HRConfigurationService

router = APIRouter()


@router.get(
    "/hr/configuration",
    response_model=HRConfigurationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Active HR Configuration",
    description="Retrieves the currently active organization-wide HR configuration policy.",
    dependencies=[Depends(has_permission("hr_configuration.read"))]
)
async def get_active_hr_configuration(
    organization_code: Optional[str] = Query(None, description="Optional organization code filter"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HRConfigurationResponse:
    """Gets the active HR Configuration."""
    service = HRConfigurationService(db)
    config = await service.get_active_configuration(organization_code=organization_code)
    if not config:
        raise ApnaERPException(
            message="No active HR configuration found for organization.",
            status_code=404,
            error_code="ACTIVE_CONFIG_NOT_FOUND",
        )
    return HRConfigurationResponse.model_validate(config)


@router.get(
    "/hr/configurations/{id}",
    response_model=HRConfigurationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get HR Configuration By ID",
    description="Retrieves specific HR configuration policy details by UUID.",
    dependencies=[Depends(has_permission("hr_configuration.read"))]
)
async def get_hr_configuration_by_id(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HRConfigurationResponse:
    """Gets HR configuration details by ID."""
    service = HRConfigurationService(db)
    config = await service.get_configuration_by_id(config_id=id)
    return HRConfigurationResponse.model_validate(config)


@router.post(
    "/hr/configuration",
    response_model=HRConfigurationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create HR Configuration",
    description="Defines a new organization-wide HR configuration policy. If active, deactivates previous active policy.",
    dependencies=[Depends(has_permission("hr_configuration.create"))]
)
async def create_hr_configuration(
    data: HRConfigurationCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HRConfigurationResponse:
    """Creates a new HR configuration."""
    service = HRConfigurationService(db)
    config = await service.create_configuration(
        data=data, current_user=current_user, request=request
    )
    return HRConfigurationResponse.model_validate(config)


@router.put(
    "/hr/configuration/{id}",
    response_model=HRConfigurationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update HR Configuration",
    description="Updates existing HR configuration policy parameters.",
    dependencies=[Depends(has_permission("hr_configuration.update"))]
)
async def update_hr_configuration(
    id: uuid.UUID,
    data: HRConfigurationUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HRConfigurationResponse:
    """Updates an existing HR configuration."""
    service = HRConfigurationService(db)
    config = await service.update_configuration(
        config_id=id, data=data, current_user=current_user, request=request
    )
    return HRConfigurationResponse.model_validate(config)


@router.patch(
    "/hr/configuration/{id}/activate",
    response_model=HRConfigurationResponse,
    status_code=status.HTTP_200_OK,
    summary="Activate HR Configuration",
    description="Activates target HR configuration policy and deactivates previous active configuration.",
    dependencies=[Depends(has_permission("hr_configuration.activate"))]
)
async def activate_hr_configuration(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HRConfigurationResponse:
    """Activates an HR configuration."""
    service = HRConfigurationService(db)
    config = await service.activate_configuration(
        config_id=id, current_user=current_user, request=request
    )
    return HRConfigurationResponse.model_validate(config)


@router.delete(
    "/hr/configuration/{id}",
    response_model=HRConfigurationResponse,
    status_code=status.HTTP_200_OK,
    summary="Soft Delete HR Configuration",
    description="Soft deletes an inactive HR configuration. Active configurations cannot be deleted.",
    dependencies=[Depends(has_permission("hr_configuration.delete"))]
)
async def delete_hr_configuration(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HRConfigurationResponse:
    """Soft deletes an inactive HR configuration."""
    service = HRConfigurationService(db)
    config = await service.delete_configuration(
        config_id=id, current_user=current_user, request=request
    )
    return HRConfigurationResponse.model_validate(config)


@router.patch(
    "/hr/configuration/{id}/restore",
    response_model=HRConfigurationResponse,
    status_code=status.HTTP_200_OK,
    summary="Restore HR Configuration",
    description="Restores a soft-deleted HR configuration record.",
    dependencies=[Depends(has_permission("hr_configuration.restore"))]
)
async def restore_hr_configuration(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HRConfigurationResponse:
    """Restores a soft-deleted HR configuration."""
    service = HRConfigurationService(db)
    config = await service.restore_configuration(
        config_id=id, current_user=current_user, request=request
    )
    return HRConfigurationResponse.model_validate(config)
