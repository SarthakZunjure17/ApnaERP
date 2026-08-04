import math
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_permission
from app.models.user import User
from app.schemas.procurement import (
    PaginatedPurchaseOrderResponse,
    PurchaseOrderCreate,
    PurchaseOrderResponse,
    PurchaseOrderUpdate,
)
from app.schemas.warehouse_operations import GoodsReceiptResponse
from app.services.purchase_order_services import purchase_order_service

router = APIRouter()


@router.post("", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    obj_in: PurchaseOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.purchase_order.create")),
):
    return await purchase_order_service.create_order(db, obj_in, current_user_id=current_user.id)


@router.get("", response_model=PaginatedPurchaseOrderResponse)
async def list_orders(
    supplier_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    origin_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.purchase_order.read")),
):
    skip = (page - 1) * size
    items, total = await purchase_order_service.list_orders(
        db,
        supplier_id=supplier_id,
        status=status,
        origin_type=origin_type,
        search=search,
        skip=skip,
        limit=size,
    )
    pages = math.ceil(total / size) if total > 0 else 0
    return PaginatedPurchaseOrderResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.get("/{po_id}", response_model=PurchaseOrderResponse)
async def get_order(
    po_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.purchase_order.read")),
):
    return await purchase_order_service.get_order(db, po_id)


@router.post("/{po_id}/submit", response_model=PurchaseOrderResponse)
async def submit_order(
    po_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.purchase_order.create")),
):
    return await purchase_order_service.submit_order(db, po_id, current_user_id=current_user.id)


@router.post("/{po_id}/approve", response_model=PurchaseOrderResponse)
async def approve_order(
    po_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.purchase_order.approve")),
):
    return await purchase_order_service.approve_order(db, po_id, approver_id=current_user.id)


@router.post("/{po_id}/cancel", response_model=PurchaseOrderResponse)
async def cancel_order(
    po_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.purchase_order.cancel")),
):
    return await purchase_order_service.cancel_order(db, po_id, current_user_id=current_user.id)


@router.post("/{po_id}/close", response_model=PurchaseOrderResponse)
async def close_order(
    po_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.purchase_order.close")),
):
    return await purchase_order_service.close_order(db, po_id, current_user_id=current_user.id)


@router.post("/{po_id}/reopen", response_model=PurchaseOrderResponse)
async def reopen_order(
    po_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.purchase_order.update")),
):
    return await purchase_order_service.reopen_order(db, po_id, current_user_id=current_user.id)


@router.post("/{po_id}/receive-goods", response_model=GoodsReceiptResponse, status_code=status.HTTP_201_CREATED)
async def receive_goods(
    po_id: uuid.UUID,
    receiving_items: List[Dict[str, Any]] = Body(..., example=[{"po_item_id": "uuid", "quantity": 10.0}]),
    supplier_ref: Optional[str] = Query(None),
    remarks: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("inventory.execute.warehouse")),
):
    return await purchase_order_service.receive_goods(
        db,
        po_id=po_id,
        receiving_items=receiving_items,
        supplier_ref=supplier_ref,
        remarks=remarks,
        current_user_id=current_user.id,
    )
