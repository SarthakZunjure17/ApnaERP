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
from app.services.quotation_services import quotation_service

router = APIRouter()


@router.post("", response_model=SupplierQuotationResponse, status_code=status.HTTP_201_CREATED)
async def create_quotation(
    obj_in: SupplierQuotationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.quotation.create")),
):
    return await quotation_service.create_quotation(db, obj_in, current_user_id=current_user.id)


@router.get("", response_model=PaginatedSupplierQuotationResponse)
async def list_quotations(
    rfq_id: Optional[uuid.UUID] = Query(None),
    supplier_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.quotation.read")),
):
    skip = (page - 1) * size
    items, total = await quotation_service.list_quotations(
        db, rfq_id=rfq_id, supplier_id=supplier_id, status=status, skip=skip, limit=size
    )
    pages = math.ceil(total / size) if total > 0 else 0
    return PaginatedSupplierQuotationResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.get("/{quotation_id}", response_model=SupplierQuotationResponse)
async def get_quotation(
    quotation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.quotation.read")),
):
    return await quotation_service.get_quotation(db, quotation_id)


@router.post("/{quotation_id}/approve", response_model=SupplierQuotationResponse)
async def approve_quotation(
    quotation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.quotation.approve")),
):
    return await quotation_service.approve_quotation(db, quotation_id, current_user_id=current_user.id)
