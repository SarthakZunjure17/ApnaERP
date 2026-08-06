from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_permission
from app.models.user import User
from app.schemas.finance import (
    AccountingDimensionCreate,
    AccountingDimensionResponse,
    CostCenterCreate,
    CostCenterResponse,
)
from app.services.finance_services import CostCenterService

router = APIRouter()
cc_service = CostCenterService()


@router.post("", response_model=CostCenterResponse, status_code=status.HTTP_201_CREATED)
async def create_cost_center(
    obj_in: CostCenterCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.costcenter.create")),
) -> Any:
    try:
        return await cc_service.create_cost_center(db, obj_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[CostCenterResponse])
async def list_cost_centers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.costcenter.read")),
) -> Any:
    return await cc_service.cost_repo.get_all(db)


@router.post("/dimensions", response_model=AccountingDimensionResponse, status_code=status.HTTP_201_CREATED)
async def create_accounting_dimension(
    obj_in: AccountingDimensionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.costcenter.create")),
) -> Any:
    try:
        return await cc_service.create_dimension(db, obj_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/dimensions", response_model=List[AccountingDimensionResponse])
async def list_accounting_dimensions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.costcenter.read")),
) -> Any:
    return await cc_service.dim_repo.get_all(db)
