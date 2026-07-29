from typing import List
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission
from app.models.user import User
from app.schemas.inventory import (
    ProductAttributeCreate,
    ProductAttributeResponse,
    ProductAttributeUpdate,
    ProductAttributeValueCreate,
    ProductAttributeValueResponse,
)
from app.services.inventory_services import product_attribute_service

router = APIRouter()


# --- Global Attribute Definitions CRUD ---

@router.get("", response_model=List[ProductAttributeResponse], status_code=status.HTTP_200_OK)
async def get_product_attributes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.attribute.read")),
):
    """Retrieve list of product attribute definitions."""
    return await product_attribute_service.get_attributes(db, skip=skip, limit=limit)


@router.get("/{id}", response_model=ProductAttributeResponse, status_code=status.HTTP_200_OK)
async def get_product_attribute(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.attribute.read")),
):
    """Retrieve product attribute definition by ID."""
    return await product_attribute_service.get_attribute(db, id)


@router.post("", response_model=ProductAttributeResponse, status_code=status.HTTP_201_CREATED)
async def create_product_attribute(
    attribute_in: ProductAttributeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.attribute.create")),
):
    """Create a new product attribute definition."""
    return await product_attribute_service.create_attribute(db, obj_in=attribute_in, current_user_id=current_user.id)


@router.put("/{id}", response_model=ProductAttributeResponse, status_code=status.HTTP_200_OK)
async def update_product_attribute(
    id: uuid.UUID,
    attribute_in: ProductAttributeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.attribute.update")),
):
    """Update an existing product attribute definition."""
    return await product_attribute_service.update_attribute(db, id, obj_in=attribute_in, current_user_id=current_user.id)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product_attribute(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.attribute.delete")),
):
    """Delete a product attribute definition."""
    await product_attribute_service.delete_attribute(db, id, current_user_id=current_user.id)


# --- Product Specific Attribute Mapping Endpoints ---

@router.post("/products/{product_id}/attributes", response_model=ProductAttributeValueResponse, status_code=status.HTTP_201_CREATED)
async def set_product_attribute_value(
    product_id: uuid.UUID,
    attr_val_in: ProductAttributeValueCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.attribute.create")),
):
    """Set or update attribute value for a specific product."""
    return await product_attribute_service.set_product_attribute(
        db, product_id, obj_in=attr_val_in, current_user_id=current_user.id
    )


@router.delete("/products/{product_id}/attributes/{attribute_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product_attribute_value(
    product_id: uuid.UUID,
    attribute_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.attribute.delete")),
):
    """Remove attribute value from a product."""
    await product_attribute_service.delete_product_attribute(
        db, product_id, attribute_id, current_user_id=current_user.id
    )

