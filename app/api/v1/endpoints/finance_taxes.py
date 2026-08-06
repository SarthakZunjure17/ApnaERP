from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_permission
from app.models.user import User
from app.schemas.finance import (
    TaxCategoryCreate,
    TaxCategoryResponse,
    TaxRateCreate,
    TaxRateResponse,
)
from app.services.finance_services import TaxService

router = APIRouter()
tax_service = TaxService()


@router.post("/categories", response_model=TaxCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_tax_category(
    obj_in: TaxCategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.tax.create")),
) -> Any:
    try:
        return await tax_service.create_tax_category(db, obj_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/categories", response_model=List[TaxCategoryResponse])
async def list_tax_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.tax.read")),
) -> Any:
    return await tax_service.cat_repo.get_all(db)


@router.post("/rates", response_model=TaxRateResponse, status_code=status.HTTP_201_CREATED)
async def create_tax_rate(
    obj_in: TaxRateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.tax.create")),
) -> Any:
    try:
        return await tax_service.create_tax_rate(db, obj_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/rates", response_model=List[TaxRateResponse])
async def list_tax_rates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.tax.read")),
) -> Any:
    return await tax_service.rate_repo.get_all(db)
