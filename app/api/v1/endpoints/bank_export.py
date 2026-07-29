from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, has_permission
from app.models.user import User
from app.schemas.payroll_finalization import BankExportRequest, BankExportResponse
from app.services.payroll_finalization_services import BankExportService

router = APIRouter(prefix="/payroll", tags=["Bank Export"])


@router.post("/bank-export", response_model=BankExportResponse, status_code=status.HTTP_201_CREATED)
async def generate_bank_export(
    request: BankExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("payroll.bank.export")),
):
    service = BankExportService(db)
    return await service.generate_bank_export(request, current_user=current_user)
