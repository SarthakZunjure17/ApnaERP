import math
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.schemas.inventory_advanced import (
    PaginatedStockReservationResponse,
    StockReservationCreate,
    StockReservationResponse,
)
from app.services.inventory_advanced_services import stock_reservation_service

router = APIRouter()


@router.post(
    "",
    response_model=StockReservationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("inventory.reservation.create"))],
)
async def create_stock_reservation(
    obj_in: StockReservationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reserve stock for upcoming demand (Sales/Manufacturing/Procurement/Internal)."""
    return await stock_reservation_service.create_reservation(db, obj_in=obj_in, current_user_id=current_user.id)


@router.post(
    "/{reservation_id}/cancel",
    response_model=StockReservationResponse,
    dependencies=[Depends(has_permission("inventory.reservation.cancel"))],
)
async def cancel_stock_reservation(
    reservation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel an active stock reservation."""
    return await stock_reservation_service.cancel_reservation(db, reservation_id=reservation_id)


@router.get(
    "",
    response_model=PaginatedStockReservationResponse,
    dependencies=[Depends(has_permission("inventory.reservation.read"))],
)
async def list_stock_reservations(
    product_id: Optional[uuid.UUID] = Query(None),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List stock reservations with filtering and pagination."""
    skip = (page - 1) * size
    items, total = await stock_reservation_service.list_reservations(
        db, product_id=product_id, warehouse_id=warehouse_id, status=status_filter, skip=skip, limit=size
    )
    pages = math.ceil(total / size) if total > 0 else 1
    return PaginatedStockReservationResponse(items=items, total=total, page=page, size=size, pages=pages)
