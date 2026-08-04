from datetime import datetime, timezone
from decimal import Decimal
import json
import logging
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_manager
from app.models.procurement_report_snapshot import ProcurementReportSnapshot
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.models.purchase_requisition import PurchaseRequisition
from app.models.purchase_return import PurchaseReturn
from app.models.rfq import RFQ
from app.models.supplier import Supplier
from app.repositories.procurement_repos import procurement_report_snapshot_repository
from app.schemas.procurement import (
    ProcurementDashboardSummary,
    PurchaseRegisterItem,
    SupplierLedgerItem,
)

logger = logging.getLogger("app.services.procurement_reports")


class ProcurementReportService:
    """
    Domain service generating operational reports (Purchase Register, Supplier Ledger, Open POs, Returns).
    """
    async def get_purchase_register(
        self, db: AsyncSession, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> List[PurchaseRegisterItem]:
        stmt = (
            select(
                PurchaseOrder.po_number,
                PurchaseOrder.order_date,
                Supplier.name.label("supplier_name"),
                PurchaseOrder.total_amount,
                PurchaseOrder.status,
            )
            .join(Supplier, PurchaseOrder.supplier_id == Supplier.id)
            .where(PurchaseOrder.status.in_(["Approved", "Partially Received", "Fully Received", "Closed"]))
        )
        if start_date:
            stmt = stmt.where(PurchaseOrder.order_date >= start_date)
        if end_date:
            stmt = stmt.where(PurchaseOrder.order_date <= end_date)

        stmt = stmt.order_by(PurchaseOrder.order_date.desc())
        res = await db.execute(stmt)
        rows = res.all()

        return [
            PurchaseRegisterItem(
                po_number=r.po_number,
                order_date=r.order_date,
                supplier_name=r.supplier_name,
                total_amount=Decimal(str(r.total_amount)),
                status=r.status,
            )
            for r in rows
        ]

    async def get_supplier_ledger(self, db: AsyncSession) -> List[SupplierLedgerItem]:
        stmt = select(Supplier).where(Supplier.is_deleted == False)
        res = await db.execute(stmt)
        suppliers = res.scalars().all()

        items: List[SupplierLedgerItem] = []
        for s in suppliers:
            po_count_stmt = select(func.count(PurchaseOrder.id)).where(PurchaseOrder.supplier_id == s.id)
            po_count_res = await db.execute(po_count_stmt)
            po_count = po_count_res.scalar() or 0

            items.append(
                SupplierLedgerItem(
                    supplier_id=s.id,
                    supplier_name=s.name,
                    total_orders=po_count,
                    total_spend=Decimal(str(s.total_spend)),
                    ontime_rate=Decimal(str(s.ontime_delivery_rate)),
                    quality_rate=Decimal(str(s.quality_rating)),
                )
            )

        return items


class ProcurementAnalyticsService:
    """
    Executive Analytics Service providing cached dashboard telemetry and snapshot generation.
    """
    async def get_dashboard_summary(self, db: AsyncSession) -> ProcurementDashboardSummary:
        cache_key = "procurement:dashboard:summary"
        cached = await redis_manager.get_json(cache_key)
        if cached:
            return ProcurementDashboardSummary(**cached)

        # 1. Total Spend
        spend_stmt = select(func.coalesce(func.sum(PurchaseOrder.total_amount), Decimal("0.0"))).where(
            PurchaseOrder.status.in_(["Approved", "Partially Received", "Fully Received", "Closed"])
        )
        spend_res = await db.execute(spend_stmt)
        tot_spend = Decimal(str(spend_res.scalar() or 0.0))

        # 2. Open PO Count
        open_po_stmt = select(func.count(PurchaseOrder.id)).where(
            PurchaseOrder.status.in_(["Submitted", "Approved", "Partially Received"])
        )
        open_po_res = await db.execute(open_po_stmt)
        open_po_cnt = open_po_res.scalar() or 0

        # 3. Open Requisitions Count
        open_req_stmt = select(func.count(PurchaseRequisition.id)).where(
            PurchaseRequisition.status.in_(["Submitted", "Approved", "Partially Fulfilled"])
        )
        open_req_res = await db.execute(open_req_stmt)
        open_req_cnt = open_req_res.scalar() or 0

        # 4. Active Suppliers Count
        act_supp_stmt = select(func.count(Supplier.id)).where(Supplier.status == "Active").where(Supplier.is_deleted == False)
        act_supp_res = await db.execute(act_supp_stmt)
        act_supp_cnt = act_supp_res.scalar() or 0

        # 5. Delayed Orders Count
        now = datetime.now(timezone.utc)
        delay_stmt = (
            select(func.count(PurchaseOrder.id))
            .where(PurchaseOrder.status.in_(["Approved", "Partially Received"]))
            .where(PurchaseOrder.expected_delivery_date.isnot(None))
            .where(PurchaseOrder.expected_delivery_date < now)
        )
        delay_res = await db.execute(delay_stmt)
        delay_cnt = delay_res.scalar() or 0

        summary = ProcurementDashboardSummary(
            total_purchase_spend=tot_spend,
            open_po_count=open_po_cnt,
            open_requisitions_count=open_req_cnt,
            active_suppliers_count=act_supp_cnt,
            delayed_orders_count=delay_cnt,
            spend_by_department=[],
            top_vendors=[],
            purchase_trends=[],
        )

        await redis_manager.set_json(cache_key, json.loads(summary.model_dump_json()), expire=300)
        return summary

    async def generate_analytics_snapshot(self, db: AsyncSession) -> ProcurementReportSnapshot:
        summary = await self.get_dashboard_summary(db)
        snapshot = ProcurementReportSnapshot(
            snapshot_date=datetime.now(timezone.utc),
            total_purchase_spend=summary.total_purchase_spend,
            open_po_count=summary.open_po_count,
            open_requisitions_count=summary.open_requisitions_count,
            active_suppliers_count=summary.active_suppliers_count,
            delayed_orders_count=summary.delayed_orders_count,
            metrics_json=json.loads(summary.model_dump_json()),
        )
        return await procurement_report_snapshot_repository.create(db, obj_in=snapshot)


procurement_report_service = ProcurementReportService()
procurement_analytics_service = ProcurementAnalyticsService()
