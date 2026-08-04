from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_permission
from app.models.user import User
from app.schemas.procurement import PurchaseRegisterItem, SupplierLedgerItem
from app.services.procurement_report_services import procurement_report_service

router = APIRouter()


@router.get("/purchase-register", response_model=List[PurchaseRegisterItem])
async def get_purchase_register(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.reports.read")),
):
    return await procurement_report_service.get_purchase_register(db, start_date=start_date, end_date=end_date)


@router.get("/supplier-ledger", response_model=List[SupplierLedgerItem])
async def get_supplier_ledger(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.reports.read")),
):
    return await procurement_report_service.get_supplier_ledger(db)
