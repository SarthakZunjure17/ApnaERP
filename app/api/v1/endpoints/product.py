from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission
from app.models.user import User
from app.schemas.inventory import (
    ProductCreate,
    ProductDetailResponse,
    ProductResponse,
    ProductUpdate,
)
from app.services.inventory_services import product_service

router = APIRouter()


@router.get("", status_code=status.HTTP_200_OK)
async def get_products(
    search: Optional[str] = Query(None, description="Search term for SKU, Barcode, Name, Description"),
    category_id: Optional[uuid.UUID] = Query(None),
    brand_id: Optional[uuid.UUID] = Query(None),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    track_inventory: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.product.read")),
):
    """Retrieve paginated products with filtering and multi-column search."""
    items, total = await product_service.get_products(
        db,
        search_term=search,
        category_id=category_id,
        brand_id=brand_id,
        warehouse_id=warehouse_id,
        status=status_filter,
        track_inventory=track_inventory,
        skip=skip,
        limit=limit,
    )
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/{id}", response_model=ProductDetailResponse, status_code=status.HTTP_200_OK)
async def get_product_by_id(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.product.read")),
):
    """Retrieve detailed product record by ID including attributes and documents."""
    return await product_service.get_product_detail(db, id)


@router.post("", response_model=ProductDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_in: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.product.create")),
):
    """Create a new product in the product master catalog."""
    return await product_service.create_product(db, obj_in=product_in, current_user_id=current_user.id)


@router.put("/{id}", response_model=ProductDetailResponse, status_code=status.HTTP_200_OK)
async def update_product(
    id: uuid.UUID,
    product_in: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.product.update")),
):
    """Update an existing product record."""
    return await product_service.update_product(db, id, obj_in=product_in, current_user_id=current_user.id)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.product.delete")),
):
    """Delete a product record."""
    await product_service.delete_product(db, id, current_user_id=current_user.id)

