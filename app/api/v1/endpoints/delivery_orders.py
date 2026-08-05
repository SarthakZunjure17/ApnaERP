import math
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_permission
from app.models.user import User
from app.schemas.sales import DeliveryOrderCreate, DeliveryOrderResponse
from app.services.delivery_services import delivery_service

router = APIRouter()


@router.post("", response_model=DeliveryOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_delivery_order(
    obj_in: DeliveryOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.delivery.create")),
):
    return await delivery_service.create_delivery(db, obj_in, current_user_id=current_user.id)


@router.get("", response_model=dict)
async def list_delivery_orders(
    query: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    sales_order_id: Optional[uuid.UUID] = Query(None),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.delivery.read")),
):
    skip = (page - 1) * page_size
    items, total = await delivery_service.list_deliveries(
        db, query=query, status=status_filter, sales_order_id=sales_order_id, warehouse_id=warehouse_id, skip=skip, limit=page_size
    )
    pages = math.ceil(total / page_size) if total > 0 else 1
    return {
        "items": [DeliveryOrderResponse.model_validate(d) for d in items],
        "total": total,
        "page": page,
        "size": page_size,
        "pages": pages,
    }


@router.get("/{delivery_id}", response_model=DeliveryOrderResponse)
async def get_delivery_order(
    delivery_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.delivery.read")),
):
    return await delivery_service.get_delivery(db, delivery_id)


@router.post("/{delivery_id}/cancel", response_model=DeliveryOrderResponse)
async def cancel_delivery_order(
    delivery_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.delivery.update")),
):
    return await delivery_service.cancel_delivery(db, delivery_id, current_user_id=current_user.id)
