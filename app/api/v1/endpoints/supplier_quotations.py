import math
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_permission
from app.models.user import User
from app.schemas.procurement import (
    PaginatedSupplierQuotationResponse,
    SupplierQuotationCreate,
    SupplierQuotationResponse,
    SupplierQuotationUpdate,
)
from app.services.supplier_quotation_services import supplier_quotation_service

router = APIRouter()


@router.post("", response_model=SupplierQuotationResponse, status_code=status.HTTP_201_CREATED)
async def create_quotation(
    obj_in: SupplierQuotationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.quotation.create")),
):
    return await supplier_quotation_service.create_quotation(db, obj_in, current_user_id=current_user.id)


@router.get("", response_model=PaginatedSupplierQuotationResponse)
async def list_quotations(
    rfq_id: Optional[uuid.UUID] = Query(None),
    supplier_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.quotation.read")),
):
    skip = (page - 1) * size
    items, total = await supplier_quotation_service.list_quotations(
        db, rfq_id=rfq_id, supplier_id=supplier_id, status=status, search=search, skip=skip, limit=size
    )
    pages = math.ceil(total / size) if total > 0 else 0
    return PaginatedSupplierQuotationResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.get("/{quotation_id}", response_model=SupplierQuotationResponse)
async def get_quotation(
    quotation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.quotation.read")),
):
    return await supplier_quotation_service.get_quotation(db, quotation_id)


@router.put("/{quotation_id}", response_model=SupplierQuotationResponse)
async def update_quotation(
    quotation_id: uuid.UUID,
    obj_in: SupplierQuotationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.quotation.update")),
):
    return await supplier_quotation_service.update_quotation(
        db, quotation_id, obj_in, current_user_id=current_user.id
    )


@router.post("/{quotation_id}/submit", response_model=SupplierQuotationResponse)
async def submit_quotation(
    quotation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.quotation.submit")),
):
    return await supplier_quotation_service.submit_quotation(db, quotation_id, current_user_id=current_user.id)


@router.post("/{quotation_id}/withdraw", response_model=SupplierQuotationResponse)
async def withdraw_quotation(
    quotation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.quotation.withdraw")),
):
    return await supplier_quotation_service.withdraw_quotation(db, quotation_id, current_user_id=current_user.id)


@router.post("/{quotation_id}/approve", response_model=SupplierQuotationResponse)
async def approve_quotation(
    quotation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.quotation.approve")),
):
    return await supplier_quotation_service.approve_quotation(db, quotation_id, current_user_id=current_user.id)


@router.post("/{quotation_id}/reject", response_model=SupplierQuotationResponse)
async def reject_quotation(
    quotation_id: uuid.UUID,
    reason: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.quotation.approve")),
):
    return await supplier_quotation_service.reject_quotation(
        db, quotation_id, reason=reason, current_user_id=current_user.id
    )
