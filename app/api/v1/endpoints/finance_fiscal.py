from typing import Any, List
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_permission
from app.models.user import User
from app.schemas.finance import (
    FiscalPeriodLockRequest,
    FiscalPeriodResponse,
    FiscalYearCreate,
    FiscalYearResponse,
)
from app.services.finance_services import FiscalService

router = APIRouter()
fiscal_service = FiscalService()


@router.post("/years", response_model=FiscalYearResponse, status_code=status.HTTP_201_CREATED)
async def create_fiscal_year(
    obj_in: FiscalYearCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.fiscal.create")),
) -> Any:
    try:
        return await fiscal_service.create_fiscal_year(db, obj_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/years", response_model=List[FiscalYearResponse])
async def list_fiscal_years(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.fiscal.read")),
) -> Any:
    return await fiscal_service.year_repo.get_all(db)


@router.put("/periods/{period_id}/lock", response_model=FiscalPeriodResponse)
async def lock_fiscal_period(
    period_id: uuid.UUID,
    obj_in: FiscalPeriodLockRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.fiscal.lock")),
) -> Any:
    try:
        return await fiscal_service.lock_period(db, period_id, obj_in.is_locked, current_user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
