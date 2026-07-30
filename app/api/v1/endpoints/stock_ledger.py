from datetime import datetime
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission
from app.models.user import User
from app.schemas.stock_engine import PaginatedStockLedgerResponse, StockLedgerResponse
from app.services.stock_engine_services import stock_ledger_service

router = APIRouter()


@router.get("", response_model=PaginatedStockLedgerResponse, status_code=status.HTTP_200_OK)
async def get_stock_ledger(
    product_id: Optional[uuid.UUID] = Query(None),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    storage_location_id: Optional[uuid.UUID] = Query(None),
    transaction_type_id: Optional[uuid.UUID] = Query(None),
    reference_type: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    search: Optional[str] = Query(None, description="Search by reference_type, remarks, direction"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.ledger.read")),
):
    """Retrieve paginated immutable stock ledger entries with multi-column filtering and search."""
    items, total = await stock_ledger_service.get_ledger_entries(
        db,
        product_id=product_id,
        warehouse_id=warehouse_id,
        storage_location_id=storage_location_id,
        transaction_type_id=transaction_type_id,
        reference_type=reference_type,
        start_date=start_date,
        end_date=end_date,
        search_term=search,
        skip=skip,
        limit=limit,
    )
    res_items = []
    for item in items:
        resp = StockLedgerResponse.model_validate(item)
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

    return PaginatedStockLedgerResponse(items=res_items, total=total, skip=skip, limit=limit)
