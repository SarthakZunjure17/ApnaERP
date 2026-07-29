import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, has_permission
from app.models.user import User
from app.schemas.payroll_finalization import (
    PayrollClosingRequest,
    PayrollClosingResponse,
    PayrollReopenRequest,
)
from app.services.payroll_finalization_services import PayrollClosingService

router = APIRouter(prefix="/payroll-periods", tags=["Payroll Closing"])


@router.post("/{period_id}/close", response_model=PayrollClosingResponse)
async def close_payroll_period(
    period_id: uuid.UUID,
    request: PayrollClosingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("payroll.close")),
):
    service = PayrollClosingService(db)
    return await service.close_payroll(period_id, remarks=request.closing_remarks, current_user=current_user)


@router.post("/{period_id}/reopen", response_model=PayrollClosingResponse)
async def reopen_payroll_period(
    period_id: uuid.UUID,
    request: PayrollReopenRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("payroll.reopen")),
):
    service = PayrollClosingService(db)
    return await service.reopen_payroll(period_id, reopen_reason=request.reopen_reason, current_user=current_user)


@router.post("/{period_id}/archive", response_model=PayrollClosingResponse)
async def archive_payroll_period(
    period_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("payroll.archive")),
):
    service = PayrollClosingService(db)
    return await service.archive_payroll(period_id, current_user=current_user)
