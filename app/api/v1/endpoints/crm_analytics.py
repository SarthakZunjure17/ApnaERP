from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.crm import CRMAnalyticsSummary
from app.services.crm_services import CRMAnalyticsService

router = APIRouter()
analytics_service = CRMAnalyticsService()


@router.get("/summary", response_model=CRMAnalyticsSummary)
async def get_summary_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get executive CRM summary analytics."""
    return await analytics_service.get_summary_analytics(db)
