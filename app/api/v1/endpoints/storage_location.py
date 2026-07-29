from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission
from app.models.user import User
from app.schemas.inventory import (
    StorageLocationCreate,
    StorageLocationResponse,
    StorageLocationTreeResponse,
    StorageLocationUpdate,
)
from app.services.inventory_services import storage_location_service

router = APIRouter()


@router.get("", response_model=List[StorageLocationResponse], status_code=status.HTTP_200_OK)
async def get_storage_locations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.location.read")),
):
    """Retrieve list of storage locations."""
    return await storage_location_service.get_locations(db, skip=skip, limit=limit)


@router.get("/tree", response_model=List[StorageLocationTreeResponse], status_code=status.HTTP_200_OK)
async def get_storage_location_tree(
    warehouse_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.location.read")),
):
    """Retrieve full hierarchical tree of storage locations for a warehouse."""
    return await storage_location_service.get_location_tree(db, warehouse_id=warehouse_id)


@router.get("/{id}", response_model=StorageLocationResponse, status_code=status.HTTP_200_OK)
async def get_storage_location(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.location.read")),
):
    """Retrieve storage location by ID."""
    return await storage_location_service.get_location(db, id)


@router.post("", response_model=StorageLocationResponse, status_code=status.HTTP_201_CREATED)
async def create_storage_location(
    location_in: StorageLocationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.location.create")),
):
    """Create a new storage location."""
    return await storage_location_service.create_location(db, obj_in=location_in, current_user_id=current_user.id)


@router.put("/{id}", response_model=StorageLocationResponse, status_code=status.HTTP_200_OK)
async def update_storage_location(
    id: uuid.UUID,
    location_in: StorageLocationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.location.update")),
):
    """Update an existing storage location."""
    return await storage_location_service.update_location(db, id, obj_in=location_in, current_user_id=current_user.id)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_storage_location(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.location.delete")),
):
    """Delete a storage location."""
    await storage_location_service.delete_location(db, id, current_user_id=current_user.id)

