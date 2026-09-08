from datetime import date
from typing import Any, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_permission
from app.models.user import User
from app.schemas.finance import (
    AccountLedgerResponse,
    GeneralLedgerEntryResponse,
    TrialBalanceReportResponse,
)
from app.services.finance_services import GeneralLedgerService

router = APIRouter()
gl_service = GeneralLedgerService()


@router.get("/transactions", response_model=List[GeneralLedgerEntryResponse])
async def get_general_ledger_transactions(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    account_id: Optional[uuid.UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.ledger.read")),
) -> Any:
    entries, _ = await gl_service.get_all_transactions(
        db, from_date=from_date, to_date=to_date, account_id=account_id, skip=skip, limit=limit
    )
    return entries


@router.get("/accounts/{account_id}", response_model=AccountLedgerResponse)
async def get_account_ledger(
    account_id: uuid.UUID,
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.ledger.read")),
) -> Any:
    try:
        return await gl_service.get_account_ledger(
            db, account_id=account_id, from_date=from_date, to_date=to_date, skip=skip, limit=limit
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/trial-balance", response_model=TrialBalanceReportResponse)
async def get_trial_balance_report(
    as_of_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.reports.read")),
) -> Any:
    return await gl_service.get_trial_balance(db, as_of_date=as_of_date)
