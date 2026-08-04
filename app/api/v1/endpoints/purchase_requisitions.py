import math
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_permission
from app.models.user import User
from app.schemas.procurement import (
    PaginatedPurchaseRequisitionResponse,
    PurchaseRequisitionCreate,
    PurchaseRequisitionResponse,
    PurchaseRequisitionUpdate,
)
from app.services.purchase_requisition_services import purchase_requisition_service

router = APIRouter()


@router.post("", response_model=PurchaseRequisitionResponse, status_code=status.HTTP_201_CREATED)
async def create_requisition(
    obj_in: PurchaseRequisitionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.requisition.create")),
):
    return await purchase_requisition_service.create_requisition(db, obj_in, requester_id=current_user.id)


@router.get("", response_model=PaginatedPurchaseRequisitionResponse)
async def list_requisitions(
    department_id: Optional[uuid.UUID] = Query(None),
    requester_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.requisition.read")),
):
    skip = (page - 1) * size
    items, total = await purchase_requisition_service.list_requisitions(
        db,
        department_id=department_id,
        requester_id=requester_id,
        status=status,
        priority=priority,
        skip=skip,
        limit=size,
    )
    pages = math.ceil(total / size) if total > 0 else 0
    return PaginatedPurchaseRequisitionResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.get("/{requisition_id}", response_model=PurchaseRequisitionResponse)
async def get_requisition(
    requisition_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.requisition.read")),
):
    return await purchase_requisition_service.get_requisition(db, requisition_id)


@router.post("/{requisition_id}/submit", response_model=PurchaseRequisitionResponse)
async def submit_requisition(
    requisition_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.requisition.create")),
):
    return await purchase_requisition_service.submit_requisition(db, requisition_id, requester_id=current_user.id)


@router.post("/{requisition_id}/approve", response_model=PurchaseRequisitionResponse)
async def approve_requisition(
    requisition_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.requisition.approve")),
):
    return await purchase_requisition_service.approve_requisition(db, requisition_id, approver_id=current_user.id)


@router.post("/{requisition_id}/cancel", response_model=PurchaseRequisitionResponse)
async def cancel_requisition(
    requisition_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.requisition.cancel")),
):
    return await purchase_requisition_service.cancel_requisition(db, requisition_id, user_id=current_user.id)
