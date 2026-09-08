from typing import Any, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_permission
from app.models.user import User
from app.schemas.finance import (
    FiscalPeriodCreate,
    FiscalPeriodLockRequest,
    FiscalPeriodResponse,
    FiscalYearCreate,
    FiscalYearResponse,
)
from app.services.finance_services import FiscalService

router = APIRouter()
fiscal_service = FiscalService()


# --- Fiscal Years ---
@router.post("/years", response_model=FiscalYearResponse, status_code=status.HTTP_201_CREATED)
async def create_fiscal_year(
    obj_in: FiscalYearCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.fiscal.create")),
) -> Any:
    try:
        return await fiscal_service.create_fiscal_year(db, obj_in, current_user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/years", response_model=List[FiscalYearResponse])
async def list_fiscal_years(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.fiscal.read")),
) -> Any:
    return await fiscal_service.year_repo.get_all(db)


@router.get("/years/{year_id}", response_model=FiscalYearResponse)
async def get_fiscal_year(
    year_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.fiscal.read")),
) -> Any:
    fy = await fiscal_service.year_repo.get_by_id(db, year_id)
    if not fy:
        raise HTTPException(status_code=404, detail="Fiscal Year not found")
    return fy


@router.put("/years/{year_id}/close", response_model=FiscalYearResponse)
async def close_fiscal_year(
    year_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.fiscal.close")),
) -> Any:
    try:
        return await fiscal_service.close_fiscal_year(db, year_id, current_user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Fiscal Periods ---
@router.post("/periods", response_model=FiscalPeriodResponse, status_code=status.HTTP_201_CREATED)
async def create_fiscal_period(
    obj_in: FiscalPeriodCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.fiscal.create")),
) -> Any:
    try:
        return await fiscal_service.create_fiscal_period(db, obj_in, current_user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/periods", response_model=List[FiscalPeriodResponse])
async def list_fiscal_periods(
    fiscal_year_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.fiscal.read")),
) -> Any:
    if fiscal_year_id:
        return await fiscal_service.period_repo.get_periods_for_year(db, fiscal_year_id)
    return await fiscal_service.period_repo.get_all(db)


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


@router.put("/periods/{period_id}/close", response_model=FiscalPeriodResponse)
async def close_fiscal_period(
    period_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.fiscal.close")),
) -> Any:
    try:
        return await fiscal_service.close_period(db, period_id, current_user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
