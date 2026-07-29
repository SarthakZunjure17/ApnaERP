import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, has_permission
from app.models.user import User
from app.schemas.payroll_finalization import FinancialPostingQueueResponse
from app.services.payroll_finalization_services import FinancialIntegrationService

router = APIRouter(prefix="/payroll-periods", tags=["Financial Integration"])


@router.post("/{period_id}/publish-financial-payload", response_model=FinancialPostingQueueResponse, status_code=status.HTTP_201_CREATED)
async def publish_financial_payload(
    period_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("payroll.financial.publish")),
):
    service = FinancialIntegrationService(db)
    return await service.publish_financial_payload(period_id, current_user=current_user)
