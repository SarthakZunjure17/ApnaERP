from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_permission
from app.models.user import User
from app.schemas.procurement import ProcurementDashboardSummary
from app.services.procurement_report_services import procurement_analytics_service

router = APIRouter()


@router.get("/dashboard-summary", response_model=ProcurementDashboardSummary)
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.analytics.read")),
):
    return await procurement_analytics_service.get_dashboard_summary(db)
