from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, has_permission
from app.models.user import User
from app.schemas.payroll_finalization import (
    PayrollAdjustmentCreate,
    PayrollAdjustmentResponse,
    PayrollAdjustmentUpdate,
)
from app.services.payroll_finalization_services import PayrollAdjustmentService
from app.utils.pagination import PaginatedResult, PaginationParams

router = APIRouter(prefix="/payroll-adjustments", tags=["Payroll Adjustments"])


@router.get("", response_model=PaginatedResult[PayrollAdjustmentResponse])
async def get_payroll_adjustments(
    payroll_period_id: Optional[uuid.UUID] = Query(None),
    employee_id: Optional[uuid.UUID] = Query(None),
    adjustment_type: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("payroll.read")),
):
    service = PayrollAdjustmentService(db)
    return await service.adj_repo.get_filtered_adjustments(
        db,
        params=PaginationParams(page=page, page_size=page_size),
        payroll_period_id=payroll_period_id,
        employee_id=employee_id,
        adjustment_type=adjustment_type,
        status=status_filter,
    )


@router.post("", response_model=PayrollAdjustmentResponse, status_code=status.HTTP_201_CREATED)
async def create_payroll_adjustment(
    data: PayrollAdjustmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("payroll.adjustment.create")),
):
    service = PayrollAdjustmentService(db)
    return await service.create_adjustment(data, current_user=current_user)


@router.put("/{adjustment_id}", response_model=PayrollAdjustmentResponse)
async def update_payroll_adjustment(
    adjustment_id: uuid.UUID,
    data: PayrollAdjustmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("payroll.adjustment.update")),
):
    service = PayrollAdjustmentService(db)
    return await service.update_adjustment(adjustment_id, data, current_user=current_user)


@router.post("/{adjustment_id}/approve", response_model=PayrollAdjustmentResponse)
async def approve_payroll_adjustment(
    adjustment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("payroll.adjustment.update")),
):
    service = PayrollAdjustmentService(db)
    return await service.approve_adjustment(adjustment_id, current_user=current_user)


@router.post("/{adjustment_id}/reject", response_model=PayrollAdjustmentResponse)
async def reject_payroll_adjustment(
    adjustment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("payroll.adjustment.update")),
):
    service = PayrollAdjustmentService(db)
    return await service.reject_adjustment(adjustment_id, current_user=current_user)


@router.delete("/{adjustment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payroll_adjustment(
    adjustment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("payroll.adjustment.delete")),
):
    service = PayrollAdjustmentService(db)
    await service.delete_adjustment(adjustment_id, current_user=current_user)
