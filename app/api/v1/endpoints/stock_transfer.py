from datetime import datetime
from typing import Any, Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission
from app.models.user import User
from app.schemas.warehouse_operations import (
    PaginatedStockTransferResponse,
    StockTransferCreate,
    StockTransferResponse,
    StockTransferUpdate,
)
from app.services.warehouse_operations_services import stock_transfer_service

router = APIRouter()


@router.post(
    "",
    response_model=StockTransferResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Draft Stock Transfer proposal",
)
async def create_stock_transfer(
    obj_in: StockTransferCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.transfer.create")),
) -> Any:
    return await stock_transfer_service.create_transfer(db, obj_in, current_user_id=current_user.id)


@router.get(
    "",
    response_model=PaginatedStockTransferResponse,
    summary="List Stock Transfers with pagination and filters",
)
async def list_stock_transfers(
    source_warehouse_id: Optional[uuid.UUID] = Query(None, description="Filter by source warehouse ID"),
    destination_warehouse_id: Optional[uuid.UUID] = Query(None, description="Filter by destination warehouse ID"),
    status: Optional[str] = Query(None, description="Filter by document status: Draft, In Transit, Completed, Cancelled"),
    start_date: Optional[datetime] = Query(None, description="Filter by start transfer date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end transfer date"),
    search: Optional[str] = Query(None, description="Search term for transfer number"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.transfer.read")),
) -> Any:
    items, total = await stock_transfer_service.get_transfers(
        db,
        source_warehouse_id=source_warehouse_id,
        destination_warehouse_id=destination_warehouse_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
        search=search,
        skip=skip,
        limit=limit,
    )
    return PaginatedStockTransferResponse(items=items, total=total, skip=skip, limit=limit)


@router.get(
    "/{id}",
    response_model=StockTransferResponse,
    summary="Get Stock Transfer details by ID",
)
async def get_stock_transfer(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.transfer.read")),
) -> Any:
    return await stock_transfer_service.get_transfer(db, id)


@router.put(
    "/{id}",
    response_model=StockTransferResponse,
    summary="Update a Draft Stock Transfer",
)
async def update_stock_transfer(
    id: uuid.UUID,
    obj_in: StockTransferUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.transfer.update")),
) -> Any:
    return await stock_transfer_service.update_transfer(db, id, obj_in, current_user_id=current_user.id)


@router.post(
    "/{id}/approve",
    response_model=StockTransferResponse,
    summary="Approve a Draft Stock Transfer document",
)
async def approve_stock_transfer(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.transfer.approve")),
) -> Any:
    return await stock_transfer_service.approve_transfer(db, id, current_user_id=current_user.id)


@router.post(
    "/{id}/dispatch",
    response_model=StockTransferResponse,
    summary="Dispatch Stock Transfer out of source warehouse (In Transit status)",
)
async def dispatch_stock_transfer(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.transfer.dispatch")),
) -> Any:
    return await stock_transfer_service.dispatch_transfer(db, id, current_user_id=current_user.id)


@router.post(
    "/{id}/receive",
    response_model=StockTransferResponse,
    summary="Receive/Complete Stock Transfer into destination warehouse (Completed status)",
)
async def receive_stock_transfer(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.transfer.receive")),
) -> Any:
    return await stock_transfer_service.complete_transfer(db, id, current_user_id=current_user.id)


@router.post(
    "/{id}/complete",
    response_model=StockTransferResponse,
    summary="Complete Stock Transfer into destination warehouse (Completed status)",
)
async def complete_stock_transfer(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.transfer.complete")),
) -> Any:
    return await stock_transfer_service.complete_transfer(db, id, current_user_id=current_user.id)


@router.post(
    "/{id}/cancel",
    response_model=StockTransferResponse,
    summary="Cancel a Stock Transfer document",
)
async def cancel_stock_transfer(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.transfer.cancel")),
) -> Any:
    return await stock_transfer_service.cancel_transfer(db, id, current_user_id=current_user.id)
