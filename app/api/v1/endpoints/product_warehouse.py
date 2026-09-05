from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission
from app.models.user import User
from app.schemas.inventory import (
    InventoryPolicyCreate,
    InventoryPolicyResponse,
    ProductWarehouseCreate,
    ProductWarehouseResponse,
    ProductWarehouseUpdate,
)
from app.services.inventory_services import (
    inventory_policy_service,
    product_warehouse_service,
)

router = APIRouter()
policy_router = APIRouter()


# --- Product-Warehouse Configurations ---

@router.get("", response_model=List[ProductWarehouseResponse], status_code=status.HTTP_200_OK)
async def list_product_warehouses(
    product_id: Optional[uuid.UUID] = Query(None),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.product_warehouse.read")),
):
    """List product warehouse stocking configurations."""
    if product_id:
        return await product_warehouse_service.list_by_product(db, product_id=product_id, skip=skip, limit=limit)
    if warehouse_id:
        return await product_warehouse_service.list_by_warehouse(db, warehouse_id=warehouse_id, skip=skip, limit=limit)
    return await product_warehouse_service.list_product_warehouses(db, skip=skip, limit=limit)


@router.post("", response_model=ProductWarehouseResponse, status_code=status.HTTP_201_CREATED)
async def create_product_warehouse(
    obj_in: ProductWarehouseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.product_warehouse.create")),
):
    """Create a new product-warehouse stocking configuration."""
    return await product_warehouse_service.create_product_warehouse(
        db, obj_in=obj_in, current_user_id=current_user.id
    )


@router.get("/{id}", response_model=ProductWarehouseResponse, status_code=status.HTTP_200_OK)
async def get_product_warehouse(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.product_warehouse.read")),
):
    """Retrieve product warehouse configuration by ID."""
    return await product_warehouse_service.get_product_warehouse(db, id)


@router.put("/{id}", response_model=ProductWarehouseResponse, status_code=status.HTTP_200_OK)
async def update_product_warehouse(
    id: uuid.UUID,
    obj_in: ProductWarehouseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.product_warehouse.update")),
):
    """Update an existing product warehouse configuration."""
    return await product_warehouse_service.update_product_warehouse(
        db, id, obj_in=obj_in, current_user_id=current_user.id
    )


@router.patch("/{id}", response_model=ProductWarehouseResponse, status_code=status.HTTP_200_OK)
async def patch_product_warehouse(
    id: uuid.UUID,
    obj_in: ProductWarehouseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.product_warehouse.update")),
):
    """Partially update an existing product warehouse configuration."""
    return await product_warehouse_service.update_product_warehouse(
        db, id, obj_in=obj_in, current_user_id=current_user.id
    )


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product_warehouse(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.product_warehouse.delete")),
):
    """Delete a product warehouse configuration."""
    await product_warehouse_service.delete_product_warehouse(db, id, current_user_id=current_user.id)


# --- Inventory Policy Routes ---

@policy_router.get("", response_model=List[InventoryPolicyResponse], status_code=status.HTTP_200_OK)
async def list_inventory_policies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.policy.read")),
):
    """List all inventory policies (global and warehouse-specific)."""
    return await inventory_policy_service.list_policies(db, skip=skip, limit=limit)


@policy_router.get("/{warehouse_id}", response_model=Optional[InventoryPolicyResponse], status_code=status.HTTP_200_OK)
async def get_inventory_policy(
    warehouse_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.policy.read")),
):
    """Retrieve inventory policy for a warehouse or fallback to global policy."""
    return await inventory_policy_service.get_policy(db, warehouse_id=warehouse_id)


@policy_router.post("", response_model=InventoryPolicyResponse, status_code=status.HTTP_200_OK)
async def create_or_update_inventory_policy(
    obj_in: InventoryPolicyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.policy.update")),
):
    """Create or update inventory policy configuration."""
    return await inventory_policy_service.create_or_update_policy(
        db, obj_in=obj_in, current_user_id=current_user.id
    )
