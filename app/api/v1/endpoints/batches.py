import math
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.schemas.inventory_advanced import BatchCreate, BatchResponse, BatchUpdate, PaginatedBatchResponse
from app.services.inventory_advanced_services import batch_service

router = APIRouter()


@router.post(
    "",
    response_model=BatchResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("inventory.batch.create"))],
)
async def create_batch(
    obj_in: BatchCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new product batch."""
    return await batch_service.create_batch(db, obj_in=obj_in)


@router.get(
    "/{batch_id}",
    response_model=BatchResponse,
    dependencies=[Depends(has_permission("inventory.batch.read"))],
)
async def get_batch(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve a batch by ID."""
    return await batch_service.get_batch(db, batch_id=batch_id)


@router.put(
    "/{batch_id}",
    response_model=BatchResponse,
    dependencies=[Depends(has_permission("inventory.batch.update"))],
)
async def update_batch(
    batch_id: uuid.UUID,
    obj_in: BatchUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a batch record."""
    return await batch_service.update_batch(db, batch_id=batch_id, obj_in=obj_in)


@router.get(
    "",
    response_model=PaginatedBatchResponse,
    dependencies=[Depends(has_permission("inventory.batch.read"))],
)
async def list_batches(
    product_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List batches with filtering and pagination."""
    skip = (page - 1) * size
    items, total = await batch_service.list_batches(
        db, product_id=product_id, status=status_filter, search=search, skip=skip, limit=size
    )
    pages = math.ceil(total / size) if total > 0 else 1
    return PaginatedBatchResponse(items=items, total=total, page=page, size=size, pages=pages)
