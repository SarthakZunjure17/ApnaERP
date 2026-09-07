import math
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_permission
from app.models.user import User
from app.schemas.procurement import (
    PaginatedRFQResponse,
    RFQComparisonMatrix,
    RFQCreate,
    RFQResponse,
    RFQSupplierInvite,
    RFQSupplierResponse,
    RFQUpdate,
)
from app.services.rfq_services import rfq_service

router = APIRouter()


@router.post("", response_model=RFQResponse, status_code=status.HTTP_201_CREATED)
async def create_rfq(
    obj_in: RFQCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.rfq.create")),
):
    return await rfq_service.create_rfq(db, obj_in, current_user_id=current_user.id)


@router.get("", response_model=PaginatedRFQResponse)
async def list_rfqs(
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.rfq.read")),
):
    skip = (page - 1) * size
    items, total = await rfq_service.list_rfqs(db, status=status, search=search, skip=skip, limit=size)
    pages = math.ceil(total / size) if total > 0 else 0
    return PaginatedRFQResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.get("/{rfq_id}", response_model=RFQResponse)
async def get_rfq(
    rfq_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.rfq.read")),
):
    return await rfq_service.get_rfq(db, rfq_id)


@router.put("/{rfq_id}", response_model=RFQResponse)
async def update_rfq(
    rfq_id: uuid.UUID,
    obj_in: RFQUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.rfq.update")),
):
    return await rfq_service.update_rfq(db, rfq_id, obj_in, current_user_id=current_user.id)


@router.post("/{rfq_id}/issue", response_model=RFQResponse)
async def issue_rfq(
    rfq_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.rfq.issue")),
):
    return await rfq_service.issue_rfq(db, rfq_id, current_user_id=current_user.id)


@router.post("/{rfq_id}/cancel", response_model=RFQResponse)
async def cancel_rfq(
    rfq_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.rfq.cancel")),
):
    return await rfq_service.cancel_rfq(db, rfq_id, current_user_id=current_user.id)


@router.post("/{rfq_id}/suppliers", response_model=RFQSupplierResponse)
@router.post("/{rfq_id}/invite", response_model=RFQSupplierResponse)
async def invite_supplier(
    rfq_id: uuid.UUID,
    invite_in: RFQSupplierInvite,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.rfq.update")),
):
    return await rfq_service.invite_supplier(
        db, rfq_id, invite_in.supplier_id, current_user_id=current_user.id
    )


@router.get("/{rfq_id}/suppliers", response_model=List[RFQSupplierResponse])
async def list_invited_suppliers(
    rfq_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.rfq.read")),
):
    return await rfq_service.list_invited_suppliers(db, rfq_id)


@router.delete("/{rfq_id}/suppliers/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_supplier(
    rfq_id: uuid.UUID,
    supplier_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.rfq.update")),
):
    await rfq_service.remove_supplier(db, rfq_id, supplier_id, current_user_id=current_user.id)
    return None


@router.get("/{rfq_id}/comparison", response_model=RFQComparisonMatrix)
@router.get("/{rfq_id}/comparison-matrix", response_model=RFQComparisonMatrix)
async def get_comparison_matrix(
    rfq_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.rfq.read")),
):
    return await rfq_service.get_comparison_matrix(db, rfq_id)


@router.post("/{rfq_id}/award/{quotation_id}", response_model=RFQResponse)
async def award_quotation(
    rfq_id: uuid.UUID,
    quotation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.quotation.award")),
):
    return await rfq_service.award_quotation(
        db, rfq_id, quotation_id, current_user_id=current_user.id
    )
