from typing import List
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission
from app.models.user import User
from app.schemas.inventory import (
    ProductWarehouseResponse,
    StorageLocationResponse,
    StorageLocationTreeResponse,
    WarehouseCreate,
    WarehouseResponse,
    WarehouseUpdate,
)
from app.services.inventory_services import storage_location_service, warehouse_service

router = APIRouter()


@router.get("", response_model=List[WarehouseResponse], status_code=status.HTTP_200_OK)
async def get_warehouses(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.warehouse.read")),
):
    """Retrieve list of warehouses."""
    return await warehouse_service.get_warehouses(db, skip=skip, limit=limit)


@router.get("/{id}", response_model=WarehouseResponse, status_code=status.HTTP_200_OK)
async def get_warehouse(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.warehouse.read")),
):
    """Retrieve warehouse by ID."""
    return await warehouse_service.get_warehouse(db, id)


@router.get("/{id}/locations", response_model=List[StorageLocationResponse], status_code=status.HTTP_200_OK)
async def get_warehouse_locations(
    id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.warehouse.read")),
):
    """Retrieve all storage locations within a warehouse."""
    return await warehouse_service.get_locations(db, warehouse_id=id, skip=skip, limit=limit)


@router.get("/{id}/locations/tree", response_model=List[StorageLocationTreeResponse], status_code=status.HTTP_200_OK)
async def get_warehouse_location_tree(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.warehouse.read")),
):
    """Retrieve hierarchical tree of storage locations within a warehouse."""
    await warehouse_service.get_warehouse(db, id)
    return await storage_location_service.get_location_tree(db, warehouse_id=id)


@router.get("/{id}/products", response_model=List[ProductWarehouseResponse], status_code=status.HTTP_200_OK)
async def get_warehouse_products(
    id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.warehouse.read")),
):
    """Retrieve all product stocking configurations assigned to a warehouse."""
    return await warehouse_service.get_products(db, warehouse_id=id, skip=skip, limit=limit)


@router.post("", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED)
async def create_warehouse(
    warehouse_in: WarehouseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.warehouse.create")),
):
    """Create a new warehouse facility."""
    return await warehouse_service.create_warehouse(db, obj_in=warehouse_in, current_user_id=current_user.id)


@router.put("/{id}", response_model=WarehouseResponse, status_code=status.HTTP_200_OK)
async def update_warehouse(
    id: uuid.UUID,
    warehouse_in: WarehouseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.warehouse.update")),
):
    """Update an existing warehouse facility."""
    return await warehouse_service.update_warehouse(db, id, obj_in=warehouse_in, current_user_id=current_user.id)


@router.patch("/{id}", response_model=WarehouseResponse, status_code=status.HTTP_200_OK)
async def patch_warehouse(
    id: uuid.UUID,
    warehouse_in: WarehouseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.warehouse.update")),
):
    """Partially update an existing warehouse facility."""
    return await warehouse_service.update_warehouse(db, id, obj_in=warehouse_in, current_user_id=current_user.id)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_warehouse(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.warehouse.delete")),
):
    """Delete or safely deactivate a warehouse facility."""
    await warehouse_service.delete_warehouse(db, id, current_user_id=current_user.id)
