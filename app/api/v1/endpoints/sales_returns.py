import math
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_permission
from app.models.user import User
from app.schemas.sales import SalesReturnCreate, SalesReturnResponse
from app.services.sales_return_services import sales_return_service

router = APIRouter()


@router.post("", response_model=SalesReturnResponse, status_code=status.HTTP_201_CREATED)
async def create_sales_return(
    obj_in: SalesReturnCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.return.create")),
):
    return await sales_return_service.create_return(db, obj_in, current_user_id=current_user.id)


@router.get("", response_model=dict)
async def list_sales_returns(
    query: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    sales_order_id: Optional[uuid.UUID] = Query(None),
    customer_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.return.read")),
):
    skip = (page - 1) * page_size
    items, total = await sales_return_service.list_returns(
        db, query=query, status=status_filter, sales_order_id=sales_order_id, customer_id=customer_id, skip=skip, limit=page_size
    )
    pages = math.ceil(total / page_size) if total > 0 else 1
    return {
        "items": [SalesReturnResponse.model_validate(r) for r in items],
        "total": total,
        "page": page,
        "size": page_size,
        "pages": pages,
    }


@router.get("/{return_id}", response_model=SalesReturnResponse)
async def get_sales_return(
    return_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.return.read")),
):
    return await sales_return_service.get_return(db, return_id)


@router.post("/{return_id}/approve", response_model=SalesReturnResponse)
async def approve_sales_return(
    return_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.return.approve")),
):
    return await sales_return_service.approve_return(db, return_id, current_user_id=current_user.id)
