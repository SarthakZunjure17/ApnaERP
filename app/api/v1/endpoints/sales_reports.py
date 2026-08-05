from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_permission
from app.models.user import User
from app.schemas.sales import CustomerLedgerEntry
from app.services.sales_analytics_services import sales_report_service

router = APIRouter()


@router.get("/quotations", response_model=List[dict])
async def get_quotation_report(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.analytics.read")),
):
    return await sales_report_service.get_quotation_report(db, status=status_filter)


@router.get("/orders", response_model=List[dict])
async def get_order_report(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.analytics.read")),
):
    return await sales_report_service.get_order_report(db, status=status_filter)


@router.get("/deliveries", response_model=List[dict])
async def get_delivery_report(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.analytics.read")),
):
    return await sales_report_service.get_delivery_report(db, status=status_filter)


@router.get("/sales-register", response_model=List[dict])
async def get_sales_register(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.analytics.read")),
):
    return await sales_report_service.get_sales_register(db)


@router.get("/customer-ledger/{customer_id}", response_model=List[CustomerLedgerEntry])
async def get_customer_ledger(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.analytics.read")),
):
    return await sales_report_service.get_customer_ledger(db, customer_id)


@router.get("/returns", response_model=List[dict])
async def get_return_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.analytics.read")),
):
    return await sales_report_service.get_return_report(db)
