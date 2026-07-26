from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, has_permission
from app.models.user import User
from app.schemas.shift import (
    ShiftCreate,
    ShiftListResponse,
    ShiftResponse,
    ShiftUpdate,
)
from app.services.shift import ShiftService

router = APIRouter()


@router.get(
    "",
    response_model=ShiftListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Shift Schedules",
    description="Retrieves a paginated list of enterprise shift schedules with search and filtering.",
    dependencies=[Depends(has_permission("shift.read"))]
)
async def get_shifts(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by code, name, or description"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShiftListResponse:
    """Gets paginated shifts."""
    service = ShiftService(db)
    result = await service.get_shifts(page=page, page_size=page_size, search=search, is_active=is_active)
    return ShiftListResponse(
        items=[ShiftResponse.model_validate(s) for s in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@router.get(
    "/{id}",
    response_model=ShiftResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Shift Details",
    description="Retrieves specific shift schedule details by UUID.",
    dependencies=[Depends(has_permission("shift.read"))]
)
async def get_shift_by_id(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShiftResponse:
    """Gets shift details by ID."""
    service = ShiftService(db)
    shift = await service.get_shift_by_id(shift_id=id)
    return ShiftResponse.model_validate(shift)


@router.post(
    "",
    response_model=ShiftResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Shift Schedule",
    description="Defines a new enterprise shift schedule.",
    dependencies=[Depends(has_permission("shift.create"))]
)
async def create_shift(
    data: ShiftCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShiftResponse:
    """Creates a new shift schedule."""
    service = ShiftService(db)
    shift = await service.create_shift(data=data, current_user=current_user, request=request)
    return ShiftResponse.model_validate(shift)


@router.put(
    "/{id}",
    response_model=ShiftResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Shift Schedule",
    description="Updates existing shift schedule parameters.",
    dependencies=[Depends(has_permission("shift.update"))]
)
async def update_shift(
    id: uuid.UUID,
    data: ShiftUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShiftResponse:
    """Updates an existing shift schedule."""
    service = ShiftService(db)
    shift = await service.update_shift(shift_id=id, data=data, current_user=current_user, request=request)
    return ShiftResponse.model_validate(shift)


@router.delete(
    "/{id}",
    response_model=ShiftResponse,
    status_code=status.HTTP_200_OK,
    summary="Soft Delete Shift Schedule",
    description="Soft deletes an unassigned shift schedule. Shifts assigned to active employees cannot be deleted.",
    dependencies=[Depends(has_permission("shift.delete"))]
)
async def delete_shift(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShiftResponse:
    """Soft deletes a shift schedule."""
    service = ShiftService(db)
    shift = await service.delete_shift(shift_id=id, current_user=current_user, request=request)
    return ShiftResponse.model_validate(shift)


@router.patch(
    "/{id}/restore",
    response_model=ShiftResponse,
    status_code=status.HTTP_200_OK,
    summary="Restore Shift Schedule",
    description="Restores a soft-deleted shift schedule record.",
    dependencies=[Depends(has_permission("shift.restore"))]
)
async def restore_shift(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShiftResponse:
    """Restores a soft-deleted shift schedule."""
    service = ShiftService(db)
    shift = await service.restore_shift(shift_id=id, current_user=current_user, request=request)
    return ShiftResponse.model_validate(shift)
