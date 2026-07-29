from typing import List
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, has_permission
from app.models.user import User
from app.schemas.inventory import (
    ProductCategoryCreate,
    ProductCategoryResponse,
    ProductCategoryTreeResponse,
    ProductCategoryUpdate,
)
from app.services.inventory_services import category_service

router = APIRouter()


@router.get("", response_model=List[ProductCategoryResponse], status_code=status.HTTP_200_OK)
async def get_categories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.category.read")),
):
    """Retrieve list of product categories."""
    return await category_service.get_categories(db, skip=skip, limit=limit)


@router.get("/tree", response_model=List[ProductCategoryTreeResponse], status_code=status.HTTP_200_OK)
async def get_category_tree(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.category.read")),
):
    """Retrieve full hierarchical tree of product categories."""
    return await category_service.get_category_tree(db)


@router.get("/{id}", response_model=ProductCategoryResponse, status_code=status.HTTP_200_OK)
async def get_category(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.category.read")),
):
    """Retrieve product category by ID."""
    return await category_service.get_category(db, id)


@router.post("", response_model=ProductCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_in: ProductCategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.category.create")),
):
    """Create a new product category."""
    return await category_service.create_category(db, obj_in=category_in, current_user_id=current_user.id)


@router.put("/{id}", response_model=ProductCategoryResponse, status_code=status.HTTP_200_OK)
async def update_category(
    id: uuid.UUID,
    category_in: ProductCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.category.update")),
):
    """Update an existing product category."""
    return await category_service.update_category(db, id, obj_in=category_in, current_user_id=current_user.id)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.category.delete")),
):
    """Delete a product category."""
    await category_service.delete_category(db, id, current_user_id=current_user.id)

