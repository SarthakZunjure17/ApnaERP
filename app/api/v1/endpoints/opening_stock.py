from typing import List
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission
from app.models.user import User
from app.schemas.stock_engine import OpeningStockCreate, OpeningStockResponse
from app.services.stock_engine_services import opening_stock_service

router = APIRouter()


@router.post("", response_model=OpeningStockResponse, status_code=status.HTTP_201_CREATED)
async def create_opening_stock(
    opening_in: OpeningStockCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.opening.create")),
):
    """Create an opening stock initialization record and execute corresponding immutable ledger entry."""
    op = await opening_stock_service.create_opening_stock(db, obj_in=opening_in, current_user_id=current_user.id)
    resp = OpeningStockResponse.model_validate(op)
    if op.product:
        resp.product_sku = op.product.sku
    if op.warehouse:
        resp.warehouse_code = op.warehouse.code
    return resp


@router.get("", response_model=List[OpeningStockResponse], status_code=status.HTTP_200_OK)
async def get_opening_stocks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.opening.create")),
):
    """Retrieve list of opening stock initialization records."""
    items = await opening_stock_service.get_opening_stocks(db, skip=skip, limit=limit)
    res = []
    for item in items:
        resp = OpeningStockResponse.model_validate(item)
        if item.product:
            resp.product_sku = item.product.sku
        if item.warehouse:
            resp.warehouse_code = item.warehouse.code
        res.append(resp)
    return res


@router.get("/{id}", response_model=OpeningStockResponse, status_code=status.HTTP_200_OK)
async def get_opening_stock_by_id(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.opening.create")),
):
    """Retrieve an opening stock record by ID."""
    op = await opening_stock_service.get_opening_stock(db, id)
    resp = OpeningStockResponse.model_validate(op)
    if op.product:
        resp.product_sku = op.product.sku
    if op.warehouse:
        resp.warehouse_code = op.warehouse.code
    return resp
