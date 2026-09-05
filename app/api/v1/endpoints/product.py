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
    ProductWarehouseResponse,
)
from app.schemas.stock_engine import ProductStockSummaryResponse
from app.services.inventory_services import product_service, product_warehouse_service


router = APIRouter()


@router.get("/search", status_code=status.HTTP_200_OK)
async def search_products(
    q: Optional[str] = Query(None, description="Search term across SKU, Barcode, Name, Model Number, Description"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.product.read")),
):
    """Dedicated search endpoint across products."""
    items, total = await product_service.get_products(
        db,
        search_term=q,
        skip=skip,
        limit=limit,
    )
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("", status_code=status.HTTP_200_OK)
async def get_products(
    search: Optional[str] = Query(None, description="Search term for SKU, Barcode, Name, Description"),
    category_id: Optional[uuid.UUID] = Query(None),
    brand_id: Optional[uuid.UUID] = Query(None),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    product_type: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    is_active: Optional[bool] = Query(None),
    is_stockable: Optional[bool] = Query(None),
    is_sellable: Optional[bool] = Query(None),
    is_purchasable: Optional[bool] = Query(None),
    track_inventory: Optional[bool] = Query(None),
    page: Optional[int] = Query(None, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.product.read")),
):
    """Retrieve paginated products with filtering and multi-column search."""
    if page is not None and page_size is not None:
        effective_skip = (page - 1) * page_size
        effective_limit = page_size
    else:
        effective_skip = skip
        effective_limit = limit

    items, total = await product_service.get_products(
        db,
        search_term=search,
        category_id=category_id,
        brand_id=brand_id,
        warehouse_id=warehouse_id,
        product_type=product_type,
        status=status_filter,
        is_active=is_active,
        is_stockable=is_stockable,
        is_sellable=is_sellable,
        is_purchasable=is_purchasable,
        track_inventory=track_inventory,
        skip=effective_skip,
        limit=effective_limit,
    )
    return {
        "items": items,
        "total": total,
        "skip": effective_skip,
        "limit": effective_limit,
        "page": page if page is not None else (effective_skip // effective_limit) + 1,
        "page_size": effective_limit,
    }


@router.get("/{id}", response_model=ProductDetailResponse, status_code=status.HTTP_200_OK)
async def get_product_by_id(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.product.read")),
):
    """Retrieve detailed product record by ID including attributes, documents, and warehouse configs."""
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


@router.patch("/{id}", response_model=ProductDetailResponse, status_code=status.HTTP_200_OK)
async def patch_product(
    id: uuid.UUID,
    product_in: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.product.update")),
):
    """Partially update an existing product record."""
    return await product_service.update_product(db, id, obj_in=product_in, current_user_id=current_user.id)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.product.delete")),
):
    """Delete or safely deactivate a product record."""
    await product_service.delete_product(db, id, current_user_id=current_user.id)


@router.get("/{id}/warehouses", response_model=List[ProductWarehouseResponse], status_code=status.HTTP_200_OK)
async def get_product_warehouses(
    id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.product.read")),
):
    """Retrieve all warehouse configurations for a product."""
    await product_service.get_product(db, id)
    return await product_warehouse_service.list_by_product(db, product_id=id, skip=skip, limit=limit)


@router.get("/{id}/stock", response_model=ProductStockSummaryResponse, status_code=status.HTTP_200_OK)
async def get_product_stock(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.product.read")),
):
    """Retrieve live authoritative stock balances across all warehouses for a product."""
    from app.services.stock_engine_services import stock_balance_service
    return await stock_balance_service.get_product_stock_summary(db, id)

