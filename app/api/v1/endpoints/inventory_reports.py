from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.schemas.inventory_advanced import (
    InventoryAgingItem,
    MovementAnalysisItem,
    StockValuationItem,
)
from app.services.inventory_report_services import inventory_report_service

router = APIRouter()


@router.get(
    "/valuation",
    response_model=List[StockValuationItem],
    dependencies=[Depends(has_permission("inventory.reports.read"))],
)
async def get_stock_valuation_report(
    warehouse_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve Stock Valuation Report."""
    return await inventory_report_service.get_stock_valuation_report(db, warehouse_id=warehouse_id)


@router.get(
    "/aging",
    response_model=List[InventoryAgingItem],
    dependencies=[Depends(has_permission("inventory.reports.read"))],
)
async def get_inventory_aging_report(
    warehouse_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve Inventory Aging Report (0-30, 31-60, 61-90, 90+ days)."""
    return await inventory_report_service.get_inventory_aging_report(db, warehouse_id=warehouse_id)


@router.get(
    "/movement",
    response_model=List[MovementAnalysisItem],
    dependencies=[Depends(has_permission("inventory.reports.read"))],
)
async def get_movement_analysis_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve Fast Moving, Slow Moving, and Dead Stock Analysis Report."""
    return await inventory_report_service.get_movement_analysis_report(db)
