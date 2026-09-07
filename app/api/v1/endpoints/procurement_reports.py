from datetime import datetime
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_permission
from app.models.user import User
from app.schemas.procurement import (
    PaginatedPurchaseOrderReportResponse,
    PaginatedPurchaseReturnReportResponse,
    PaginatedQuotationReportResponse,
    PaginatedReceivingReportResponse,
    PaginatedRequisitionReportResponse,
    PaginatedRFQReportResponse,
    PaginatedSupplierPerformanceReportResponse,
    ProcurementDashboardResponse,
    ProcurementEfficiencyMetricsResponse,
    ProcurementSpendAnalyticsResponse,
    PurchaseRegisterItem,
    SupplierLedgerItem,
)
from app.services.procurement_report_services import (
    procurement_analytics_service,
    procurement_report_service,
)

router = APIRouter()


@router.get("/dashboard", response_model=ProcurementDashboardResponse)
async def get_procurement_dashboard(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.reports.read")),
):
    return await procurement_analytics_service.get_dashboard_summary(db, date_from=date_from, date_to=date_to)


@router.get("/purchase-orders", response_model=PaginatedPurchaseOrderReportResponse)
async def get_purchase_orders_report(
    supplier_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    product_id: Optional[uuid.UUID] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.reports.read")),
):
    return await procurement_report_service.get_purchase_orders_report(
        db,
        supplier_id=supplier_id,
        status=status,
        warehouse_id=warehouse_id,
        product_id=product_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        size=size,
    )


@router.get("/purchase-register", response_model=List[PurchaseRegisterItem])
async def get_purchase_register(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.reports.read")),
):
    return await procurement_report_service.get_purchase_register(db, start_date=start_date, end_date=end_date)


@router.get("/suppliers", response_model=PaginatedSupplierPerformanceReportResponse)
async def get_suppliers_performance_report(
    supplier_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.reports.read")),
):
    return await procurement_report_service.get_supplier_performance_report(
        db, supplier_id=supplier_id, status=status, date_from=date_from, date_to=date_to, page=page, size=size
    )


@router.get("/supplier-ledger", response_model=List[SupplierLedgerItem])
async def get_supplier_ledger(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.reports.read")),
):
    return await procurement_report_service.get_supplier_ledger(db)


@router.get("/requisitions", response_model=PaginatedRequisitionReportResponse)
async def get_requisitions_report(
    department_id: Optional[uuid.UUID] = Query(None),
    requester_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.reports.read")),
):
    return await procurement_report_service.get_requisitions_report(
        db,
        department_id=department_id,
        requester_id=requester_id,
        status=status,
        priority=priority,
        date_from=date_from,
        date_to=date_to,
        page=page,
        size=size,
    )


@router.get("/rfqs", response_model=PaginatedRFQReportResponse)
async def get_rfqs_report(
    status: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.reports.read")),
):
    return await procurement_report_service.get_rfqs_report(
        db, status=status, date_from=date_from, date_to=date_to, page=page, size=size
    )


@router.get("/quotations", response_model=PaginatedQuotationReportResponse)
async def get_quotations_report(
    supplier_id: Optional[uuid.UUID] = Query(None),
    rfq_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.reports.read")),
):
    return await procurement_report_service.get_quotations_report(
        db, supplier_id=supplier_id, rfq_id=rfq_id, status=status, date_from=date_from, date_to=date_to, page=page, size=size
    )


@router.get("/receiving", response_model=PaginatedReceivingReportResponse)
async def get_receiving_report(
    supplier_id: Optional[uuid.UUID] = Query(None),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    purchase_order_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.reports.read")),
):
    return await procurement_report_service.get_receiving_report(
        db,
        supplier_id=supplier_id,
        warehouse_id=warehouse_id,
        purchase_order_id=purchase_order_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        page=page,
        size=size,
    )


@router.get("/returns", response_model=PaginatedPurchaseReturnReportResponse)
async def get_returns_report(
    supplier_id: Optional[uuid.UUID] = Query(None),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    purchase_order_id: Optional[uuid.UUID] = Query(None),
    reason_code: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.reports.read")),
):
    return await procurement_report_service.get_returns_report(
        db,
        supplier_id=supplier_id,
        warehouse_id=warehouse_id,
        purchase_order_id=purchase_order_id,
        reason_code=reason_code,
        status=status,
        date_from=date_from,
        date_to=date_to,
        page=page,
        size=size,
    )


@router.get("/spend", response_model=ProcurementSpendAnalyticsResponse)
async def get_procurement_spend_report(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    supplier_id: Optional[uuid.UUID] = Query(None),
    warehouse_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.reports.read")),
):
    return await procurement_report_service.get_spend_analytics(
        db, date_from=date_from, date_to=date_to, supplier_id=supplier_id, warehouse_id=warehouse_id
    )


@router.get("/efficiency", response_model=ProcurementEfficiencyMetricsResponse)
async def get_procurement_efficiency_report(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("procurement.reports.read")),
):
    return await procurement_report_service.get_efficiency_metrics(db, date_from=date_from, date_to=date_to)
