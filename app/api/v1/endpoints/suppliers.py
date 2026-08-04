import math
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_permission
from app.models.user import User
from app.schemas.procurement import (
    PaginatedSupplierResponse,
    SupplierCategoryCreate,
    SupplierCategoryResponse,
    SupplierCreate,
    SupplierRatingCreate,
    SupplierRatingResponse,
    SupplierResponse,
    SupplierUpdate,
)
from app.services.supplier_services import supplier_service

router = APIRouter()


@router.post("/categories", response_model=SupplierCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier_category(
    obj_in: SupplierCategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.create")),
):
    return await supplier_service.create_category(db, obj_in)


@router.get("/categories", response_model=List[SupplierCategoryResponse])
async def list_supplier_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.read")),
):
    return await supplier_service.list_categories(db)


@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    obj_in: SupplierCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.create")),
):
    return await supplier_service.create_supplier(db, obj_in, current_user_id=current_user.id)


@router.get("", response_model=PaginatedSupplierResponse)
async def list_suppliers(
    category_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    is_preferred: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.read")),
):
    skip = (page - 1) * size
    items, total = await supplier_service.list_suppliers(
        db,
        category_id=category_id,
        status=status,
        is_preferred=is_preferred,
        search=search,
        skip=skip,
        limit=size,
    )
    pages = math.ceil(total / size) if total > 0 else 0
    return PaginatedSupplierResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(
    supplier_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.read")),
):
    return await supplier_service.get_supplier(db, supplier_id)


@router.put("/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    supplier_id: uuid.UUID,
    obj_in: SupplierUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.update")),
):
    return await supplier_service.update_supplier(db, supplier_id, obj_in, current_user_id=current_user.id)


@router.post("/{supplier_id}/blacklist", response_model=SupplierResponse)
async def blacklist_supplier(
    supplier_id: uuid.UUID,
    reason: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.blacklist")),
):
    return await supplier_service.blacklist_supplier(db, supplier_id, reason, current_user_id=current_user.id)


@router.post("/{supplier_id}/ratings", response_model=SupplierRatingResponse, status_code=status.HTTP_201_CREATED)
async def rate_supplier(
    supplier_id: uuid.UUID,
    obj_in: SupplierRatingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.supplier.create")),
):
    return await supplier_service.add_rating(db, supplier_id, obj_in, reviewer_id=current_user.id)
