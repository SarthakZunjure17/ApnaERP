from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_permission
from app.models.user import User
from app.schemas.sales import SalesAnalyticsResponse
from app.services.sales_analytics_services import sales_analytics_service

router = APIRouter()


@router.get("", response_model=SalesAnalyticsResponse)
async def get_sales_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.analytics.read")),
):
    return await sales_analytics_service.get_analytics_summary(db)
