from typing import List
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission
from app.models.user import User
from app.schemas.stock_engine import (
    InventoryAdjustmentCreate,
    InventoryAdjustmentResponse,
    InventoryAdjustmentUpdate,
)
from app.services.stock_engine_services import inventory_adjustment_service

router = APIRouter()


@router.post("", response_model=InventoryAdjustmentResponse, status_code=status.HTTP_201_CREATED)
async def create_inventory_adjustment(
    adj_in: InventoryAdjustmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.adjustment.create")),
):
    """Create a new inventory adjustment draft proposal."""
    adj = await inventory_adjustment_service.create_adjustment(db, obj_in=adj_in, current_user_id=current_user.id)
    resp = InventoryAdjustmentResponse.model_validate(adj)
    if adj.product:
        resp.product_sku = adj.product.sku
        resp.product_name = adj.product.name
    if adj.warehouse:
        resp.warehouse_code = adj.warehouse.code
    return resp


@router.get("", response_model=List[InventoryAdjustmentResponse], status_code=status.HTTP_200_OK)
async def get_inventory_adjustments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.adjustment.create")),
):
    """Retrieve list of inventory adjustment proposals."""
    items = await inventory_adjustment_service.get_adjustments(db, skip=skip, limit=limit)
    res = []
    for item in items:
        resp = InventoryAdjustmentResponse.model_validate(item)
        if item.product:
            resp.product_sku = item.product.sku
            resp.product_name = item.product.name
        if item.warehouse:
            resp.warehouse_code = item.warehouse.code
        res.append(resp)
    return res


@router.get("/{id}", response_model=InventoryAdjustmentResponse, status_code=status.HTTP_200_OK)
async def get_inventory_adjustment_by_id(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.adjustment.create")),
):
    """Retrieve an inventory adjustment proposal by ID."""
    adj = await inventory_adjustment_service.get_adjustment(db, id)
    resp = InventoryAdjustmentResponse.model_validate(adj)
    if adj.product:
        resp.product_sku = adj.product.sku
        resp.product_name = adj.product.name
    if adj.warehouse:
        resp.warehouse_code = adj.warehouse.code
    return resp


@router.put("/{id}", response_model=InventoryAdjustmentResponse, status_code=status.HTTP_200_OK)
async def update_inventory_adjustment(
    id: uuid.UUID,
    adj_in: InventoryAdjustmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.adjustment.create")),
):
    """Update a draft inventory adjustment proposal."""
    adj = await inventory_adjustment_service.update_adjustment(db, id, obj_in=adj_in, current_user_id=current_user.id)
    resp = InventoryAdjustmentResponse.model_validate(adj)
    if adj.product:
        resp.product_sku = adj.product.sku
        resp.product_name = adj.product.name
    if adj.warehouse:
        resp.warehouse_code = adj.warehouse.code
    return resp


@router.post("/{id}/approve", response_model=InventoryAdjustmentResponse, status_code=status.HTTP_200_OK)
async def approve_inventory_adjustment(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.adjustment.approve")),
):
    """Approve a draft inventory adjustment proposal."""
    adj = await inventory_adjustment_service.approve_adjustment(db, id, current_user_id=current_user.id)
    resp = InventoryAdjustmentResponse.model_validate(adj)
    if adj.product:
        resp.product_sku = adj.product.sku
        resp.product_name = adj.product.name
    if adj.warehouse:
        resp.warehouse_code = adj.warehouse.code
    return resp


@router.post("/{id}/apply", response_model=InventoryAdjustmentResponse, status_code=status.HTTP_200_OK)
async def apply_inventory_adjustment(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.adjustment.apply")),
):
    """Apply an Approved inventory adjustment to the immutable StockLedger."""
    adj = await inventory_adjustment_service.apply_adjustment(db, id, current_user_id=current_user.id)
    resp = InventoryAdjustmentResponse.model_validate(adj)
    if adj.product:
        resp.product_sku = adj.product.sku
        resp.product_name = adj.product.name
    if adj.warehouse:
        resp.warehouse_code = adj.warehouse.code
    return resp
