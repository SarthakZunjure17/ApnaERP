from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.finance_ops import FinancialAnalyticsResponse
from app.services.finance_ops_services import AnalyticsService

router = APIRouter()


@router.get("/dashboard", response_model=FinancialAnalyticsResponse)
async def get_financial_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AnalyticsService(db)
    return await service.get_financial_analytics()
