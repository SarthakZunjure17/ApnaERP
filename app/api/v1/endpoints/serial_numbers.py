import math
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.schemas.inventory_advanced import (
    PaginatedSerialNumberResponse,
    SerialNumberCreate,
    SerialNumberResponse,
    SerialNumberUpdate,
)
from app.services.inventory_advanced_services import serial_number_service

router = APIRouter()


@router.post(
    "",
    response_model=SerialNumberResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("inventory.serial.create"))],
)
async def register_serial_number(
    obj_in: SerialNumberCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Register a new serial number."""
    return await serial_number_service.create_serial(db, obj_in=obj_in, current_user_id=current_user.id)


@router.get(
    "/{serial_id}",
    response_model=SerialNumberResponse,
    dependencies=[Depends(has_permission("inventory.serial.read"))],
)
async def get_serial_number(
    serial_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve a serial number by ID."""
    return await serial_number_service.get_serial(db, serial_id=serial_id)


@router.put(
    "/{serial_id}/status",
    response_model=SerialNumberResponse,
    dependencies=[Depends(has_permission("inventory.serial.update"))],
)
async def update_serial_status(
    serial_id: uuid.UUID,
    obj_in: SerialNumberUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update serial number status and location assignment."""
    return await serial_number_service.update_serial_status(
        db,
        serial_id=serial_id,
        status=obj_in.status or "Available",
        warehouse_id=obj_in.warehouse_id,
        storage_location_id=obj_in.storage_location_id,
        current_user_id=current_user.id,
    )


@router.get(
    "",
    response_model=PaginatedSerialNumberResponse,
    dependencies=[Depends(has_permission("inventory.serial.read"))],
)
async def list_serial_numbers(
    product_id: Optional[uuid.UUID] = Query(None),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List serial numbers with filtering and pagination."""
    skip = (page - 1) * size
    items, total = await serial_number_service.list_serials(
        db,
        product_id=product_id,
        warehouse_id=warehouse_id,
        status=status_filter,
        search=search,
        skip=skip,
        limit=size,
    )
    pages = math.ceil(total / size) if total > 0 else 1
    return PaginatedSerialNumberResponse(items=items, total=total, page=page, size=size, pages=pages)
