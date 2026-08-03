from datetime import datetime
from typing import Any, Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission
from app.models.user import User
from app.schemas.warehouse_operations import (
    GoodsReceiptCreate,
    GoodsReceiptResponse,
    GoodsReceiptUpdate,
    PaginatedGoodsReceiptResponse,
)
from app.services.warehouse_operations_services import goods_receipt_service

router = APIRouter()


@router.post(
    "",
    response_model=GoodsReceiptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Draft Goods Receipt",
)
async def create_goods_receipt(
    obj_in: GoodsReceiptCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.receipt.create")),
) -> Any:
    return await goods_receipt_service.create_receipt(db, obj_in, current_user_id=current_user.id)


@router.get(
    "",
    response_model=PaginatedGoodsReceiptResponse,
    summary="List Goods Receipts with pagination and filters",
)
async def list_goods_receipts(
    warehouse_id: Optional[uuid.UUID] = Query(None, description="Filter by warehouse ID"),
    status: Optional[str] = Query(None, description="Filter by document status: Draft, Received, Cancelled"),
    start_date: Optional[datetime] = Query(None, description="Filter by start receipt date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end receipt date"),
    search: Optional[str] = Query(None, description="Search term for receipt number or reference"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.receipt.read")),
) -> Any:
    items, total = await goods_receipt_service.get_receipts(
        db, warehouse_id=warehouse_id, status=status, start_date=start_date, end_date=end_date, search=search, skip=skip, limit=limit
    )
    return PaginatedGoodsReceiptResponse(items=items, total=total, skip=skip, limit=limit)


@router.get(
    "/{id}",
    response_model=GoodsReceiptResponse,
    summary="Get Goods Receipt details by ID",
)
async def get_goods_receipt(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.receipt.read")),
) -> Any:
    return await goods_receipt_service.get_receipt(db, id)


@router.put(
    "/{id}",
    response_model=GoodsReceiptResponse,
    summary="Update a Draft Goods Receipt",
)
async def update_goods_receipt(
    id: uuid.UUID,
    obj_in: GoodsReceiptUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.receipt.update")),
) -> Any:
    return await goods_receipt_service.update_receipt(db, id, obj_in, current_user_id=current_user.id)


@router.post(
    "/{id}/approve",
    response_model=GoodsReceiptResponse,
    summary="Approve a Draft Goods Receipt document",
)
async def approve_goods_receipt(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.receipt.approve")),
) -> Any:
    return await goods_receipt_service.approve_receipt(db, id, current_user_id=current_user.id)


@router.post(
    "/{id}/receive",
    response_model=GoodsReceiptResponse,
    summary="Receive/Execute Goods Receipt and generate Stock Ledger IN entries",
)
async def receive_goods_receipt(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.receipt.receive")),
) -> Any:
    return await goods_receipt_service.receive_receipt(db, id, current_user_id=current_user.id)


@router.post(
    "/{id}/cancel",
    response_model=GoodsReceiptResponse,
    summary="Cancel a Goods Receipt document",
)
async def cancel_goods_receipt(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.receipt.cancel")),
) -> Any:
    return await goods_receipt_service.cancel_receipt(db, id, current_user_id=current_user.id)
