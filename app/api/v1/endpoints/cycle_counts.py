import math
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.schemas.inventory_advanced import (
    CycleCountCreate,
    CycleCountResponse,
    PaginatedCycleCountResponse,
)
from app.services.inventory_advanced_services import cycle_count_service

router = APIRouter()


@router.post(
    "",
    response_model=CycleCountResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("inventory.cycle_count.create"))],
)
async def create_cycle_count(
    obj_in: CycleCountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new cycle count audit document."""
    return await cycle_count_service.create_cycle_count(db, obj_in=obj_in, current_user_id=current_user.id)


@router.post(
    "/{cycle_count_id}/approve",
    response_model=CycleCountResponse,
    dependencies=[Depends(has_permission("inventory.cycle_count.approve"))],
)
async def approve_cycle_count(
    cycle_count_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve cycle count audit and automatically generate & apply stock adjustments."""
    return await cycle_count_service.approve_cycle_count(db, cycle_count_id=cycle_count_id, current_user_id=current_user.id)


@router.get(
    "",
    response_model=PaginatedCycleCountResponse,
    dependencies=[Depends(has_permission("inventory.cycle_count.read"))],
)
async def list_cycle_counts(
    warehouse_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List cycle counts with pagination."""
    skip = (page - 1) * size
    items, total = await cycle_count_service.list_cycle_counts(
        db, warehouse_id=warehouse_id, status=status_filter, skip=skip, limit=size
    )
    pages = math.ceil(total / size) if total > 0 else 1
    return PaginatedCycleCountResponse(items=items, total=total, page=page, size=size, pages=pages)
