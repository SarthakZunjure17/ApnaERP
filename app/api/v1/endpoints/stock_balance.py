from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission
from app.models.user import User
from app.schemas.stock_engine import (
    ProductStockSummaryResponse,
    StockBalanceResponse,
    WarehouseStockSummaryResponse,
)
from app.services.stock_engine_services import stock_balance_service

router = APIRouter()


@router.get("", response_model=List[StockBalanceResponse], status_code=status.HTTP_200_OK)
async def get_stock_balances(
    product_id: Optional[uuid.UUID] = Query(None),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    location_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.balance.read")),
):
    """Retrieve stock balance projections filtered by product, warehouse, or location."""
    balances = await stock_balance_service.get_balances(
        db, product_id=product_id, warehouse_id=warehouse_id, location_id=location_id
    )
    res = []
    for b in balances:
        resp = StockBalanceResponse.model_validate(b)
        resp.total_quantity = b.available_quantity + b.reserved_quantity + b.damaged_quantity + b.in_transit_quantity
        if b.product:
            resp.product_sku = b.product.sku
            resp.product_name = b.product.name
        if b.warehouse:
            resp.warehouse_code = b.warehouse.code
            resp.warehouse_name = b.warehouse.name
        res.append(resp)
    return res


@router.get("/warehouse/{warehouse_id}", response_model=WarehouseStockSummaryResponse, status_code=status.HTTP_200_OK)
async def get_warehouse_stock_summary(
    warehouse_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.balance.read")),
):
    """Retrieve aggregate stock summary for a specific warehouse."""
    return await stock_balance_service.get_warehouse_stock_summary(db, warehouse_id)


@router.get("/product/{product_id}", response_model=ProductStockSummaryResponse, status_code=status.HTTP_200_OK)
async def get_product_stock_summary(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.balance.read")),
):
    """Retrieve aggregate stock summary across all warehouses for a specific product."""
    return await stock_balance_service.get_product_stock_summary(db, product_id)


@router.get("/location/{location_id}", response_model=List[StockBalanceResponse], status_code=status.HTTP_200_OK)
async def get_location_stock_balances(
    location_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.balance.read")),
):
    """Retrieve stock balances for a specific storage location."""
    balances = await stock_balance_service.get_balances(db, location_id=location_id)
    res = []
    for b in balances:
        resp = StockBalanceResponse.model_validate(b)
        resp.total_quantity = b.available_quantity + b.reserved_quantity + b.damaged_quantity + b.in_transit_quantity
        if b.product:
            resp.product_sku = b.product.sku
            resp.product_name = b.product.name
        if b.warehouse:
            resp.warehouse_code = b.warehouse.code
            resp.warehouse_name = b.warehouse.name
        res.append(resp)
    return res


@router.post("/recalculate", response_model=StockBalanceResponse, status_code=status.HTTP_200_OK)
async def recalculate_stock_balance(
    product_id: uuid.UUID = Query(...),
    warehouse_id: uuid.UUID = Query(...),
    location_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.balance.read")),
):
    """Force recalculation of a stock balance projection directly from historical StockLedger entries."""
    b = await stock_balance_service.recalculate_balance_projection(
        db, product_id=product_id, warehouse_id=warehouse_id, storage_location_id=location_id
    )
    resp = StockBalanceResponse.model_validate(b)
    resp.total_quantity = b.available_quantity + b.reserved_quantity + b.damaged_quantity + b.in_transit_quantity
    if b.product:
        resp.product_sku = b.product.sku
        resp.product_name = b.product.name
    if b.warehouse:
        resp.warehouse_code = b.warehouse.code
        resp.warehouse_name = b.warehouse.name
    return resp
