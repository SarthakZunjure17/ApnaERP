import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.finance_ops import (
    BalanceSheetResponse,
    ProfitAndLossResponse,
    TrialBalanceResponse,
)
from app.services.finance_ops_services import FinancialStatementService

router = APIRouter()


@router.get("/trial-balance", response_model=TrialBalanceResponse)
async def get_trial_balance(
    as_of_date: datetime.date = Query(default_factory=datetime.date.today),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = FinancialStatementService(db)
    return await service.generate_trial_balance(as_of_date)


@router.get("/balance-sheet", response_model=BalanceSheetResponse)
async def get_balance_sheet(
    as_of_date: datetime.date = Query(default_factory=datetime.date.today),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = FinancialStatementService(db)
    return await service.generate_balance_sheet(as_of_date)


@router.get("/profit-loss", response_model=ProfitAndLossResponse)
async def get_profit_and_loss(
    start_date: datetime.date = Query(...),
    end_date: datetime.date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = FinancialStatementService(db)
    return await service.generate_profit_and_loss(start_date, end_date)
