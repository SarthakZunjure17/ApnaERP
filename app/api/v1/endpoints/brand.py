from typing import List
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission
from app.models.user import User
from app.schemas.inventory import BrandCreate, BrandResponse, BrandUpdate
from app.services.inventory_services import brand_service

router = APIRouter()


@router.get("", response_model=List[BrandResponse], status_code=status.HTTP_200_OK)
async def get_brands(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.brand.read")),
):
    """Retrieve list of product brands."""
    return await brand_service.get_brands(db, skip=skip, limit=limit)


@router.get("/{id}", response_model=BrandResponse, status_code=status.HTTP_200_OK)
async def get_brand(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.brand.read")),
):
    """Retrieve product brand by ID."""
    return await brand_service.get_brand(db, id)


@router.post("", response_model=BrandResponse, status_code=status.HTTP_201_CREATED)
async def create_brand(
    brand_in: BrandCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.brand.create")),
):
    """Create a new product brand."""
    return await brand_service.create_brand(db, obj_in=brand_in, current_user_id=current_user.id)


@router.put("/{id}", response_model=BrandResponse, status_code=status.HTTP_200_OK)
async def update_brand(
    id: uuid.UUID,
    brand_in: BrandUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.brand.update")),
):
    """Update an existing product brand."""
    return await brand_service.update_brand(db, id, obj_in=brand_in, current_user_id=current_user.id)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_brand(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.brand.delete")),
):
    """Delete a product brand."""
    await brand_service.delete_brand(db, id, current_user_id=current_user.id)

