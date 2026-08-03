import math
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.schemas.inventory_advanced import LotCreate, LotResponse, LotUpdate, PaginatedLotResponse
from app.services.inventory_advanced_services import lot_service

router = APIRouter()


@router.post(
    "",
    response_model=LotResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("inventory.lot.create"))],
)
async def create_lot(
    obj_in: LotCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new production or supplier lot."""
    return await lot_service.create_lot(db, obj_in=obj_in)


@router.get(
    "/{lot_id}",
    response_model=LotResponse,
    dependencies=[Depends(has_permission("inventory.lot.read"))],
)
async def get_lot(
    lot_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve a lot by ID."""
    return await lot_service.get_lot(db, lot_id=lot_id)


@router.get(
    "",
    response_model=PaginatedLotResponse,
    dependencies=[Depends(has_permission("inventory.lot.read"))],
)
async def list_lots(
    product_id: Optional[uuid.UUID] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List lots with pagination."""
    skip = (page - 1) * size
    items, total = await lot_service.list_lots(db, product_id=product_id, search=search, skip=skip, limit=size)
    pages = math.ceil(total / size) if total > 0 else 1
    return PaginatedLotResponse(items=items, total=total, page=page, size=size, pages=pages)
