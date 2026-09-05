from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission
from app.models.user import User
from app.schemas.stock_engine import (
    PaginatedStockMovementResponse,
    StockMovementCreate,
    StockMovementResponse,
)
from app.services.stock_engine_services import (
    stock_ledger_service,
    stock_movement_service,
)

router = APIRouter()


@router.post(
    "/movements",
    response_model=StockMovementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute an atomic stock movement",
)
@router.post(
    "",
    response_model=StockMovementResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_stock_movement(
    movement_in: StockMovementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.stock.movement.create")),
):
    """
    Executes a transactional, concurrency-safe, idempotent stock movement (STOCK_IN, STOCK_OUT, ADJUSTMENT).
    Guarantees atomic update of StockBalance and insertion of an immutable StockLedger record.
    """
    ledger_entry = await stock_movement_service.process_movement(
        db, movement_in, current_user_id=current_user.id
    )

    resp = StockMovementResponse.model_validate(ledger_entry)
    if ledger_entry.product:
        resp.product_sku = ledger_entry.product.sku
        resp.product_name = ledger_entry.product.name
    if ledger_entry.warehouse:
        resp.warehouse_code = ledger_entry.warehouse.code
        resp.warehouse_name = ledger_entry.warehouse.name
    if ledger_entry.storage_location:
        resp.storage_location_code = ledger_entry.storage_location.code
    if ledger_entry.transaction_type:
        resp.transaction_type_code = ledger_entry.transaction_type.code
    return resp


@router.get(
    "/movements",
    response_model=PaginatedStockMovementResponse,
    status_code=status.HTTP_200_OK,
    summary="List stock movements with filtering and pagination",
)
async def list_stock_movements(
    product_id: Optional[uuid.UUID] = Query(None),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    storage_location_id: Optional[uuid.UUID] = Query(None),
    movement_type: Optional[str] = Query(None, description="STOCK_IN, STOCK_OUT, ADJUSTMENT"),
    direction: Optional[str] = Query(None, description="IN, OUT"),
    reference_type: Optional[str] = Query(None),
    reference_id: Optional[uuid.UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.stock.read")),
):
    """
    Retrieves paginated stock movement history with multi-column filtering.
    """
    items, total = await stock_ledger_service.get_ledger_entries(
        db,
        product_id=product_id,
        warehouse_id=warehouse_id,
        storage_location_id=storage_location_id,
        movement_type=movement_type,
        direction=direction,
        reference_type=reference_type,
        reference_id=reference_id,
        skip=skip,
        limit=limit,
    )

    res_items = []
    for item in items:
        resp = StockMovementResponse.model_validate(item)
        if item.product:
            resp.product_sku = item.product.sku
            resp.product_name = item.product.name
        if item.warehouse:
            resp.warehouse_code = item.warehouse.code
            resp.warehouse_name = item.warehouse.name
        if item.storage_location:
            resp.storage_location_code = item.storage_location.code
        if item.transaction_type:
            resp.transaction_type_code = item.transaction_type.code
        res_items.append(resp)

    return PaginatedStockMovementResponse(items=res_items, total=total, skip=skip, limit=limit)
