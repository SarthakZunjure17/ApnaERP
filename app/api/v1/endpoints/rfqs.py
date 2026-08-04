import math
from typing import Optional
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


@router.post("/{rfq_id}/issue", response_model=RFQResponse)
async def issue_rfq(
    rfq_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.rfq.issue")),
):
    return await rfq_service.issue_rfq(db, rfq_id, current_user_id=current_user.id)


@router.post("/{rfq_id}/invite", response_model=RFQSupplierResponse)
async def invite_supplier(
    rfq_id: uuid.UUID,
    invite_in: RFQSupplierInvite,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.rfq.update")),
):
    return await rfq_service.invite_supplier(db, rfq_id, invite_in.supplier_id)


@router.get("/{rfq_id}/comparison-matrix", response_model=RFQComparisonMatrix)
async def get_comparison_matrix(
    rfq_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.rfq.read")),
):
    return await rfq_service.get_comparison_matrix(db, rfq_id)
