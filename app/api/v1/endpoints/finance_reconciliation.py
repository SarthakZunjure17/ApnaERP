import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.finance_ops import (
    BankReconciliationResponse,
    BankStatementImportCreate,
    BankStatementResponse,
)
from app.services.finance_ops_services import ReconciliationService

router = APIRouter()


@router.post("/statements/import", response_model=BankStatementResponse, status_code=status.HTTP_201_CREATED)
async def import_bank_statement(
    data: BankStatementImportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ReconciliationService(db)
    return await service.import_statement(data)


@router.post("/accounts/{bank_account_id}/auto-match", response_model=BankReconciliationResponse)
async def perform_auto_matching(
    bank_account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ReconciliationService(db)
    return await service.perform_auto_matching(bank_account_id)
