import math
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_permission
from app.models.user import User
from app.schemas.procurement import (
    PaginatedPurchaseReturnResponse,
    PurchaseReturnCreate,
    PurchaseReturnResponse,
)
from app.services.purchase_return_services import purchase_return_service

router = APIRouter()


@router.post("", response_model=PurchaseReturnResponse, status_code=status.HTTP_201_CREATED)
async def create_return(
    obj_in: PurchaseReturnCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.purchase_return.create")),
):
    return await purchase_return_service.create_return(db, obj_in, current_user_id=current_user.id)


@router.get("", response_model=PaginatedPurchaseReturnResponse)
async def list_returns(
    supplier_id: Optional[uuid.UUID] = Query(None),
    purchase_order_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.purchase_return.read")),
):
    skip = (page - 1) * size
    items, total = await purchase_return_service.list_returns(
        db, supplier_id=supplier_id, purchase_order_id=purchase_order_id, status=status, skip=skip, limit=size
    )
    pages = math.ceil(total / size) if total > 0 else 0
    return PaginatedPurchaseReturnResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.get("/{return_id}", response_model=PurchaseReturnResponse)
async def get_return(
    return_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.purchase_return.read")),
):
    return await purchase_return_service.get_return(db, return_id)


@router.post("/{return_id}/approve", response_model=PurchaseReturnResponse)
async def approve_return(
    return_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.purchase_return.approve")),
):
    return await purchase_return_service.approve_return(db, return_id, current_user_id=current_user.id)


@router.post("/{return_id}/process", response_model=PurchaseReturnResponse)
async def process_return(
    return_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.purchase_return.approve")),
):
    return await purchase_return_service.process_return(db, return_id, current_user_id=current_user.id)
