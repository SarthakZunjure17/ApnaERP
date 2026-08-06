from typing import Any, List
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_permission
from app.models.user import User
from app.schemas.finance import (
    CurrencyCreate,
    CurrencyResponse,
    ExchangeRateConvertRequest,
    ExchangeRateCreate,
    ExchangeRateResponse,
)
from app.services.finance_services import CurrencyService

router = APIRouter()
curr_service = CurrencyService()


@router.post("", response_model=CurrencyResponse, status_code=status.HTTP_201_CREATED)
async def create_currency(
    obj_in: CurrencyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.currency.create")),
) -> Any:
    try:
        return await curr_service.create_currency(db, obj_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[CurrencyResponse])
async def list_currencies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.currency.read")),
) -> Any:
    return await curr_service.curr_repo.get_all(db)


@router.post("/rates", response_model=ExchangeRateResponse, status_code=status.HTTP_201_CREATED)
async def create_exchange_rate(
    obj_in: ExchangeRateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.currency.create")),
) -> Any:
    try:
        return await curr_service.set_exchange_rate(db, obj_in, current_user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/convert")
async def convert_currency_amount(
    req: ExchangeRateConvertRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.currency.read")),
) -> Any:
    try:
        converted = await curr_service.convert_amount(
            db, req.from_currency, req.to_currency, req.amount, dt=req.effective_date
        )
        return {
            "from_currency": req.from_currency,
            "to_currency": req.to_currency,
            "original_amount": req.amount,
            "converted_amount": converted,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
