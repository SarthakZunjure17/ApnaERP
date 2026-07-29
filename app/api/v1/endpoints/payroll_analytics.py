from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, has_permission
from app.models.user import User
from app.schemas.payroll_finalization import PayrollAnalyticsResponse
from app.services.payroll_finalization_services import PayrollAnalyticsService

router = APIRouter(prefix="/payroll-analytics", tags=["Payroll Analytics"])


@router.get("", response_model=PayrollAnalyticsResponse)
async def get_payroll_analytics(
    payroll_period_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("payroll.analytics.read")),
):
    service = PayrollAnalyticsService(db)
    return await service.get_analytics(payroll_period_id=payroll_period_id)
