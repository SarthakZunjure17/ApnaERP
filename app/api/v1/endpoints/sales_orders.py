import math
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_permission
from app.models.user import User
from app.schemas.sales import (
    SalesInvoicePayload,
    SalesOrderCreate,
    SalesOrderResponse,
    SalesOrderUpdate,
)
from app.services.sales_order_services import sales_order_service
from app.services.tax_and_invoice_services import invoice_payload_service

router = APIRouter()


@router.post("", response_model=SalesOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_sales_order(
    obj_in: SalesOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.order.create")),
):
    return await sales_order_service.create_order(db, obj_in, current_user_id=current_user.id)


@router.get("", response_model=dict)
async def list_sales_orders(
    query: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    delivery_status: Optional[str] = Query(None),
    customer_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.order.read")),
):
    skip = (page - 1) * page_size
    items, total = await sales_order_service.list_orders(
        db, query=query, status=status_filter, delivery_status=delivery_status, customer_id=customer_id, skip=skip, limit=page_size
    )
    pages = math.ceil(total / page_size) if total > 0 else 1
    return {
        "items": [SalesOrderResponse.model_validate(o) for o in items],
        "total": total,
        "page": page,
        "size": page_size,
        "pages": pages,
    }


@router.post("/from-quotation/{quotation_id}", response_model=SalesOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_sales_order_from_quotation(
    quotation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.order.create")),
):
    return await sales_order_service.create_from_quotation(db, quotation_id, current_user_id=current_user.id)


@router.get("/{order_id}", response_model=SalesOrderResponse)
async def get_sales_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.order.read")),
):
    return await sales_order_service.get_order(db, order_id)


@router.put("/{order_id}", response_model=SalesOrderResponse)
async def update_sales_order(
    order_id: uuid.UUID,
    obj_in: SalesOrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.order.update")),
):
    return await sales_order_service.update_order(db, order_id, obj_in, current_user_id=current_user.id)


@router.patch("/{order_id}", response_model=SalesOrderResponse)
async def patch_sales_order(
    order_id: uuid.UUID,
    obj_in: SalesOrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.order.update")),
):
    return await sales_order_service.update_order(db, order_id, obj_in, current_user_id=current_user.id)


@router.post("/{order_id}/submit", response_model=SalesOrderResponse)
async def submit_sales_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.order.submit")),
):
    return await sales_order_service.submit_order(db, order_id, current_user_id=current_user.id)


@router.post("/{order_id}/approve", response_model=SalesOrderResponse)
async def approve_sales_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.order.approve")),
):
    return await sales_order_service.approve_order(db, order_id, current_user_id=current_user.id)


@router.post("/{order_id}/reject", response_model=SalesOrderResponse)
async def reject_sales_order(
    order_id: uuid.UUID,
    reason: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.order.approve")),
):
    return await sales_order_service.reject_order(db, order_id, reason=reason, current_user_id=current_user.id)


@router.post("/{order_id}/cancel", response_model=SalesOrderResponse)
async def cancel_sales_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.order.cancel")),
):
    return await sales_order_service.cancel_order(db, order_id, current_user_id=current_user.id)


@router.post("/{order_id}/close", response_model=SalesOrderResponse)
async def close_sales_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.order.update")),
):
    return await sales_order_service.close_order(db, order_id, current_user_id=current_user.id)


@router.post("/{order_id}/reopen", response_model=SalesOrderResponse)
async def reopen_sales_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.order.update")),
):
    return await sales_order_service.reopen_order(db, order_id, current_user_id=current_user.id)


@router.get("/{order_id}/invoice-payload", response_model=SalesInvoicePayload)
async def get_invoice_payload(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.order.read")),
):
    """
    Invoice Interface endpoint: returns structured invoice payload consumable by future Finance domain.
    """
    return await invoice_payload_service.generate_invoice_payload(db, order_id)
