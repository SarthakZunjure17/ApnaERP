import math
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_permission
from app.models.user import User
from app.schemas.sales import (
    SalesQuotationCreate,
    SalesQuotationResponse,
    SalesQuotationUpdate,
)
from app.services.quotation_services import quotation_service

router = APIRouter()


@router.post("", response_model=SalesQuotationResponse, status_code=status.HTTP_201_CREATED)
async def create_quotation(
    obj_in: SalesQuotationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.quotation.create")),
):
    return await quotation_service.create_quotation(db, obj_in, current_user_id=current_user.id)


@router.get("", response_model=dict)
async def list_quotations(
    query: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    customer_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.quotation.read")),
):
    skip = (page - 1) * page_size
    items, total = await quotation_service.list_quotations(
        db, query=query, status=status_filter, customer_id=customer_id, skip=skip, limit=page_size
    )
    pages = math.ceil(total / page_size) if total > 0 else 1
    return {
        "items": [SalesQuotationResponse.model_validate(q) for q in items],
        "total": total,
        "page": page,
        "size": page_size,
        "pages": pages,
    }


@router.get("/{quotation_id}", response_model=SalesQuotationResponse)
async def get_quotation(
    quotation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.quotation.read")),
):
    return await quotation_service.get_quotation(db, quotation_id)


@router.put("/{quotation_id}", response_model=SalesQuotationResponse)
async def update_quotation(
    quotation_id: uuid.UUID,
    obj_in: SalesQuotationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.quotation.update")),
):
    return await quotation_service.update_quotation(db, quotation_id, obj_in, current_user_id=current_user.id)


@router.patch("/{quotation_id}", response_model=SalesQuotationResponse)
async def patch_quotation(
    quotation_id: uuid.UUID,
    obj_in: SalesQuotationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.quotation.update")),
):
    return await quotation_service.update_quotation(db, quotation_id, obj_in, current_user_id=current_user.id)


@router.post("/{quotation_id}/submit", response_model=SalesQuotationResponse)
async def submit_quotation(
    quotation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.quotation.submit")),
):
    return await quotation_service.submit_quotation(db, quotation_id, current_user_id=current_user.id)


@router.post("/{quotation_id}/approve", response_model=SalesQuotationResponse)
async def approve_quotation(
    quotation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.quotation.approve")),
):
    return await quotation_service.approve_quotation(db, quotation_id, current_user_id=current_user.id)


@router.post("/{quotation_id}/reject", response_model=SalesQuotationResponse)
async def reject_quotation(
    quotation_id: uuid.UUID,
    reason: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.quotation.approve")),
):
    return await quotation_service.reject_quotation(db, quotation_id, reason=reason, current_user_id=current_user.id)


@router.post("/{quotation_id}/cancel", response_model=SalesQuotationResponse)
async def cancel_quotation(
    quotation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.quotation.cancel")),
):
    return await quotation_service.cancel_quotation(db, quotation_id, current_user_id=current_user.id)


@router.post("/{quotation_id}/clone", response_model=SalesQuotationResponse, status_code=status.HTTP_201_CREATED)
async def clone_quotation(
    quotation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.quotation.create")),
):
    return await quotation_service.clone_quotation(db, quotation_id, current_user_id=current_user.id)
