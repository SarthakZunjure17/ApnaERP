from datetime import datetime, timezone
from decimal import Decimal
import json
import logging
import math
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.redis import redis_manager
from app.models.department import Department
from app.models.goods_receipt import GoodsReceipt, GoodsReceiptItem
from app.models.procurement_report_snapshot import ProcurementReportSnapshot
from app.models.product import Product
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.models.purchase_requisition import PurchaseRequisition, PurchaseRequisitionItem
from app.models.purchase_return import PurchaseReturn, PurchaseReturnItem
from app.models.rfq import RFQ, RFQSupplier
from app.models.supplier import Supplier, SupplierRating
from app.models.supplier_quotation import SupplierQuotation, SupplierQuotationItem
from app.models.user import User
from app.models.warehouse import Warehouse
from app.repositories.procurement_repos import procurement_report_snapshot_repository
from app.schemas.procurement import (
    MonthlySpendItem,
    PaginatedPurchaseOrderReportResponse,
    PaginatedPurchaseReturnReportResponse,
    PaginatedQuotationReportResponse,
    PaginatedReceivingReportResponse,
    PaginatedRequisitionReportResponse,
    PaginatedRFQReportResponse,
    PaginatedSupplierPerformanceReportResponse,
    ProcurementDashboardSummary,
    ProcurementEfficiencyMetricsResponse,
    ProcurementSpendAnalyticsResponse,
    PurchaseOrderItemResponse,
    PurchaseOrderReportItem,
    PurchaseRegisterItem,
    PurchaseReturnReportItem,
    QuotationReportItem,
    ReceivingReportItem,
    RequisitionReportItem,
    RFQReportItem,
    StatusSpendItem,
    SupplierLedgerItem,
    SupplierPerformanceReportItem,
    SupplierSpendItem,
    WarehouseSpendItem,
)

logger = logging.getLogger("app.services.procurement_reports")


class ProcurementReportService:
    """
    Domain service generating operational reports and analytics across all Procurement domains.
    Strictly read-only; aggregates authoritative data from database.
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

    async def get_purchase_orders_report(
        self,
        db: AsyncSession,
        supplier_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        product_id: Optional[uuid.UUID] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        size: int = 50,
    ) -> PaginatedPurchaseOrderReportResponse:
        page = max(1, page)
        size = max(1, min(size, 200))
        offset = (page - 1) * size

        stmt = select(PurchaseOrder).join(Supplier, PurchaseOrder.supplier_id == Supplier.id)

        if supplier_id:
            stmt = stmt.where(PurchaseOrder.supplier_id == supplier_id)
        if status:
            stmt = stmt.where(PurchaseOrder.status == status)
        if date_from:
            stmt = stmt.where(PurchaseOrder.order_date >= date_from)
        if date_to:
            stmt = stmt.where(PurchaseOrder.order_date <= date_to)

        if warehouse_id or product_id:
            subq = select(PurchaseOrderItem.purchase_order_id)
            if warehouse_id:
                subq = subq.where(PurchaseOrderItem.warehouse_id == warehouse_id)
            if product_id:
                subq = subq.where(PurchaseOrderItem.product_id == product_id)
            stmt = stmt.where(PurchaseOrder.id.in_(subq))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_res = await db.execute(count_stmt)
        total = count_res.scalar() or 0

        stmt = (
            stmt.options(selectinload(PurchaseOrder.supplier), selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.warehouse))
            .order_by(PurchaseOrder.order_date.desc())
            .offset(offset)
            .limit(size)
        )
        res = await db.execute(stmt)
        pos = res.scalars().all()

        report_items: List[PurchaseOrderReportItem] = []
        for po in pos:
            ord_qty = sum((Decimal(str(item.quantity)) for item in po.items), Decimal("0.0"))
            rec_qty = sum((Decimal(str(item.received_quantity)) for item in po.items), Decimal("0.0"))
            ret_qty = sum((Decimal(str(item.returned_quantity)) for item in po.items), Decimal("0.0"))
            first_wh_id = po.items[0].warehouse_id if po.items else None
            first_wh_code = po.items[0].warehouse.code if po.items and po.items[0].warehouse else None
            first_wh_name = po.items[0].warehouse.name if po.items and po.items[0].warehouse else None

            report_items.append(
                PurchaseOrderReportItem(
                    id=po.id,
                    po_number=po.po_number,
                    supplier_id=po.supplier_id,
                    supplier_name=po.supplier.name if po.supplier else "Unknown",
                    order_date=po.order_date,
                    expected_delivery_date=po.expected_delivery_date,
                    status=po.status,
                    currency=po.currency,
                    subtotal=Decimal(str(po.subtotal)),
                    discount_amount=Decimal(str(po.discount_amount)),
                    tax_amount=Decimal(str(po.tax_amount)),
                    total_amount=Decimal(str(po.total_amount)),
                    ordered_quantity=ord_qty,
                    received_quantity=rec_qty,
                    returned_quantity=ret_qty,
                    warehouse_id=first_wh_id,
                    warehouse_code=first_wh_code,
                    warehouse_name=first_wh_name,
                    items_count=len(po.items),
                )
            )

        pages = math.ceil(total / size) if total > 0 else 1
        return PaginatedPurchaseOrderReportResponse(items=report_items, total=total, page=page, size=size, pages=pages)

    async def get_supplier_performance_report(
        self,
        db: AsyncSession,
        supplier_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        size: int = 50,
    ) -> PaginatedSupplierPerformanceReportResponse:
        page = max(1, page)
        size = max(1, min(size, 200))
        offset = (page - 1) * size

        stmt = select(Supplier).where(Supplier.is_deleted == False)
        if supplier_id:
            stmt = stmt.where(Supplier.id == supplier_id)
        if status:
            stmt = stmt.where(Supplier.status == status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_res = await db.execute(count_stmt)
        total = count_res.scalar() or 0

        stmt = stmt.order_by(Supplier.name.asc()).offset(offset).limit(size)
        res = await db.execute(stmt)
        suppliers = res.scalars().all()

        report_items: List[SupplierPerformanceReportItem] = []
        for s in suppliers:
            po_q = select(PurchaseOrder).where(PurchaseOrder.supplier_id == s.id)
            if date_from:
                po_q = po_q.where(PurchaseOrder.order_date >= date_from)
            if date_to:
                po_q = po_q.where(PurchaseOrder.order_date <= date_to)

            po_q = po_q.options(selectinload(PurchaseOrder.items))
            po_res = await db.execute(po_q)
            pos = po_res.scalars().all()

            total_pos = len(pos)
            tot_spend = sum(
                (Decimal(str(p.total_amount)) for p in pos if p.status in ["Approved", "Partially Received", "Fully Received", "Closed"]),
                Decimal("0.0"),
            )
            ord_qty = Decimal("0.0")
            rec_qty = Decimal("0.0")
            ret_qty = Decimal("0.0")
            for p in pos:
                for itm in p.items:
                    ord_qty += Decimal(str(itm.quantity))
                    rec_qty += Decimal(str(itm.received_quantity))
                    ret_qty += Decimal(str(itm.returned_quantity))

            report_items.append(
                SupplierPerformanceReportItem(
                    supplier_id=s.id,
                    supplier_code=s.code,
                    supplier_name=s.name,
                    status=s.status,
                    total_pos=total_pos,
                    total_spend=tot_spend if (date_from or date_to) else Decimal(str(s.total_spend)),
                    ordered_quantity=ord_qty,
                    received_quantity=rec_qty,
                    returned_quantity=ret_qty,
                    rating=Decimal(str(s.rating)),
                    ontime_delivery_rate=Decimal(str(s.ontime_delivery_rate)),
                    quality_rating=Decimal(str(s.quality_rating)),
                )
            )

        pages = math.ceil(total / size) if total > 0 else 1
        return PaginatedSupplierPerformanceReportResponse(items=report_items, total=total, page=page, size=size, pages=pages)

    async def get_requisitions_report(
        self,
        db: AsyncSession,
        department_id: Optional[uuid.UUID] = None,
        requester_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        size: int = 50,
    ) -> PaginatedRequisitionReportResponse:
        page = max(1, page)
        size = max(1, min(size, 200))
        offset = (page - 1) * size

        stmt = select(PurchaseRequisition)
        if department_id:
            stmt = stmt.where(PurchaseRequisition.department_id == department_id)
        if requester_id:
            stmt = stmt.where(PurchaseRequisition.requester_id == requester_id)
        if status:
            stmt = stmt.where(PurchaseRequisition.status == status)
        if priority:
            stmt = stmt.where(PurchaseRequisition.priority == priority)
        if date_from:
            stmt = stmt.where(PurchaseRequisition.created_at >= date_from)
        if date_to:
            stmt = stmt.where(PurchaseRequisition.created_at <= date_to)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_res = await db.execute(count_stmt)
        total = count_res.scalar() or 0

        stmt = (
            stmt.options(
                selectinload(PurchaseRequisition.requester),
                selectinload(PurchaseRequisition.department),
                selectinload(PurchaseRequisition.items),
            )
            .order_by(PurchaseRequisition.created_at.desc())
            .offset(offset)
            .limit(size)
        )
        res = await db.execute(stmt)
        prs = res.scalars().all()

        report_items: List[RequisitionReportItem] = []
        for pr in prs:
            report_items.append(
                RequisitionReportItem(
                    id=pr.id,
                    requisition_number=pr.requisition_number,
                    requester_id=pr.requester_id,
                    requester_name=pr.requester.full_name if pr.requester else None,
                    department_id=pr.department_id,
                    department_name=pr.department.name if pr.department else None,
                    required_date=pr.required_date,
                    priority=pr.priority,
                    status=pr.status,
                    total_estimated_amount=Decimal(str(pr.total_estimated_amount)),
                    item_count=len(pr.items),
                    created_at=pr.created_at,
                )
            )

        pages = math.ceil(total / size) if total > 0 else 1
        return PaginatedRequisitionReportResponse(items=report_items, total=total, page=page, size=size, pages=pages)

    async def get_rfqs_report(
        self,
        db: AsyncSession,
        status: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        size: int = 50,
    ) -> PaginatedRFQReportResponse:
        page = max(1, page)
        size = max(1, min(size, 200))
        offset = (page - 1) * size

        stmt = select(RFQ)
        if status:
            stmt = stmt.where(RFQ.status == status)
        if date_from:
            stmt = stmt.where(RFQ.created_at >= date_from)
        if date_to:
            stmt = stmt.where(RFQ.created_at <= date_to)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_res = await db.execute(count_stmt)
        total = count_res.scalar() or 0

        stmt = (
            stmt.options(
                selectinload(RFQ.requisition),
                selectinload(RFQ.invited_suppliers),
                selectinload(RFQ.quotations),
            )
            .order_by(RFQ.created_at.desc())
            .offset(offset)
            .limit(size)
        )
        res = await db.execute(stmt)
        rfqs = res.scalars().all()

        report_items: List[RFQReportItem] = []
        for r in rfqs:
            report_items.append(
                RFQReportItem(
                    id=r.id,
                    rfq_number=r.rfq_number,
                    title=r.title,
                    requisition_id=r.requisition_id,
                    requisition_number=r.requisition.requisition_number if r.requisition else None,
                    submission_deadline=r.submission_deadline,
                    status=r.status,
                    invited_suppliers_count=len(r.invited_suppliers),
                    quotations_count=len(r.quotations),
                    created_at=r.created_at,
                )
            )

        pages = math.ceil(total / size) if total > 0 else 1
        return PaginatedRFQReportResponse(items=report_items, total=total, page=page, size=size, pages=pages)

    async def get_quotations_report(
        self,
        db: AsyncSession,
        supplier_id: Optional[uuid.UUID] = None,
        rfq_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        size: int = 50,
    ) -> PaginatedQuotationReportResponse:
        page = max(1, page)
        size = max(1, min(size, 200))
        offset = (page - 1) * size

        stmt = select(SupplierQuotation)
        if supplier_id:
            stmt = stmt.where(SupplierQuotation.supplier_id == supplier_id)
        if rfq_id:
            stmt = stmt.where(SupplierQuotation.rfq_id == rfq_id)
        if status:
            stmt = stmt.where(SupplierQuotation.status == status)
        if date_from:
            stmt = stmt.where(SupplierQuotation.quotation_date >= date_from)
        if date_to:
            stmt = stmt.where(SupplierQuotation.quotation_date <= date_to)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_res = await db.execute(count_stmt)
        total = count_res.scalar() or 0

        stmt = (
            stmt.options(selectinload(SupplierQuotation.supplier), selectinload(SupplierQuotation.rfq))
            .order_by(SupplierQuotation.quotation_date.desc())
            .offset(offset)
            .limit(size)
        )
        res = await db.execute(stmt)
        sqs = res.scalars().all()

        report_items: List[QuotationReportItem] = []
        for sq in sqs:
            report_items.append(
                QuotationReportItem(
                    id=sq.id,
                    quotation_number=sq.quotation_number,
                    rfq_id=sq.rfq_id,
                    rfq_number=sq.rfq.rfq_number if sq.rfq else None,
                    supplier_id=sq.supplier_id,
                    supplier_name=sq.supplier.name if sq.supplier else "Unknown",
                    quotation_date=sq.quotation_date,
                    validity_date=sq.validity_date,
                    lead_time_days=sq.lead_time_days,
                    currency=sq.currency,
                    subtotal=Decimal(str(sq.subtotal)),
                    tax_amount=Decimal(str(sq.tax_amount)),
                    discount_amount=Decimal(str(sq.discount_amount)),
                    total_amount=Decimal(str(sq.total_amount)),
                    status=sq.status,
                )
            )

        pages = math.ceil(total / size) if total > 0 else 1
        return PaginatedQuotationReportResponse(items=report_items, total=total, page=page, size=size, pages=pages)

    async def get_receiving_report(
        self,
        db: AsyncSession,
        supplier_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        purchase_order_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        size: int = 50,
    ) -> PaginatedReceivingReportResponse:
        page = max(1, page)
        size = max(1, min(size, 200))
        offset = (page - 1) * size

        stmt = select(GoodsReceipt)
        if warehouse_id:
            stmt = stmt.where(GoodsReceipt.warehouse_id == warehouse_id)
        if status:
            stmt = stmt.where(GoodsReceipt.status == status)
        if date_from:
            stmt = stmt.where(GoodsReceipt.receipt_date >= date_from)
        if date_to:
            stmt = stmt.where(GoodsReceipt.receipt_date <= date_to)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_res = await db.execute(count_stmt)
        total = count_res.scalar() or 0

        stmt = (
            stmt.options(selectinload(GoodsReceipt.warehouse), selectinload(GoodsReceipt.items))
            .order_by(GoodsReceipt.receipt_date.desc())
            .offset(offset)
            .limit(size)
        )
        res = await db.execute(stmt)
        grs = res.scalars().all()

        report_items: List[ReceivingReportItem] = []
        for gr in grs:
            tot_qty = sum((Decimal(str(itm.quantity)) for itm in gr.items), Decimal("0.0"))
            # Match PO if external_reference is a PO Number
            po = None
            if gr.external_reference:
                po_res = await db.execute(select(PurchaseOrder).where(PurchaseOrder.po_number == gr.external_reference).options(selectinload(PurchaseOrder.supplier)))
                po = po_res.scalar_one_or_none()

            po_id = po.id if po else (purchase_order_id if purchase_order_id else None)
            po_num = po.po_number if po else gr.external_reference
            supp_id = po.supplier_id if po else supplier_id
            supp_name = po.supplier.name if (po and po.supplier) else None

            report_items.append(
                ReceivingReportItem(
                    id=gr.id,
                    receipt_number=gr.receipt_number,
                    purchase_order_id=po_id,
                    po_number=po_num,
                    supplier_id=supp_id,
                    supplier_name=supp_name,
                    warehouse_id=gr.warehouse_id,
                    warehouse_code=gr.warehouse.code if gr.warehouse else None,
                    warehouse_name=gr.warehouse.name if gr.warehouse else None,
                    receipt_date=gr.receipt_date,
                    status=gr.status,
                    total_items=len(gr.items),
                    received_quantity=tot_qty,
                )
            )

        pages = math.ceil(total / size) if total > 0 else 1
        return PaginatedReceivingReportResponse(items=report_items, total=total, page=page, size=size, pages=pages)

    async def get_returns_report(
        self,
        db: AsyncSession,
        supplier_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        purchase_order_id: Optional[uuid.UUID] = None,
        reason_code: Optional[str] = None,
        status: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        size: int = 50,
    ) -> PaginatedPurchaseReturnReportResponse:
        page = max(1, page)
        size = max(1, min(size, 200))
        offset = (page - 1) * size

        stmt = select(PurchaseReturn)
        if supplier_id:
            stmt = stmt.where(PurchaseReturn.supplier_id == supplier_id)
        if warehouse_id:
            stmt = stmt.where(PurchaseReturn.warehouse_id == warehouse_id)
        if purchase_order_id:
            stmt = stmt.where(PurchaseReturn.purchase_order_id == purchase_order_id)
        if reason_code:
            stmt = stmt.where(PurchaseReturn.reason_code == reason_code)
        if status:
            stmt = stmt.where(PurchaseReturn.status == status)
        if date_from:
            stmt = stmt.where(PurchaseReturn.return_date >= date_from)
        if date_to:
            stmt = stmt.where(PurchaseReturn.return_date <= date_to)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_res = await db.execute(count_stmt)
        total = count_res.scalar() or 0

        stmt = (
            stmt.options(
                selectinload(PurchaseReturn.purchase_order),
                selectinload(PurchaseReturn.supplier),
                selectinload(PurchaseReturn.warehouse),
                selectinload(PurchaseReturn.items),
            )
            .order_by(PurchaseReturn.return_date.desc())
            .offset(offset)
            .limit(size)
        )
        res = await db.execute(stmt)
        returns = res.scalars().all()

        report_items: List[PurchaseReturnReportItem] = []
        for r in returns:
            ret_qty = sum((Decimal(str(itm.return_quantity)) for itm in r.items), Decimal("0.0"))
            report_items.append(
                PurchaseReturnReportItem(
                    id=r.id,
                    return_number=r.return_number,
                    purchase_order_id=r.purchase_order_id,
                    po_number=r.purchase_order.po_number if r.purchase_order else "",
                    supplier_id=r.supplier_id,
                    supplier_name=r.supplier.name if r.supplier else "",
                    warehouse_id=r.warehouse_id,
                    warehouse_code=r.warehouse.code if r.warehouse else None,
                    warehouse_name=r.warehouse.name if r.warehouse else None,
                    return_date=r.return_date,
                    reason_code=r.reason_code,
                    supplier_return_ref=r.supplier_return_ref,
                    total_return_amount=Decimal(str(r.total_return_amount)),
                    status=r.status,
                    returned_quantity=ret_qty,
                )
            )

        pages = math.ceil(total / size) if total > 0 else 1
        return PaginatedPurchaseReturnReportResponse(items=report_items, total=total, page=page, size=size, pages=pages)

    async def get_spend_analytics(
        self,
        db: AsyncSession,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        supplier_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
    ) -> ProcurementSpendAnalyticsResponse:
        base_stmt = select(PurchaseOrder).where(
            PurchaseOrder.status.in_(["Approved", "Partially Received", "Fully Received", "Closed"])
        )
        if date_from:
            base_stmt = base_stmt.where(PurchaseOrder.order_date >= date_from)
        if date_to:
            base_stmt = base_stmt.where(PurchaseOrder.order_date <= date_to)
        if supplier_id:
            base_stmt = base_stmt.where(PurchaseOrder.supplier_id == supplier_id)
        if warehouse_id:
            subq = select(PurchaseOrderItem.purchase_order_id).where(PurchaseOrderItem.warehouse_id == warehouse_id)
            base_stmt = base_stmt.where(PurchaseOrder.id.in_(subq))

        base_stmt = base_stmt.options(
            selectinload(PurchaseOrder.supplier),
            selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.warehouse),
        )
        res = await db.execute(base_stmt)
        pos = res.scalars().all()

        total_spend = sum((Decimal(str(po.total_amount)) for po in pos), Decimal("0.0"))

        # Spend by Supplier
        supp_map: Dict[uuid.UUID, Dict[str, Any]] = {}
        # Spend by Month
        month_map: Dict[str, Dict[str, Any]] = {}
        # Spend by Warehouse
        wh_map: Dict[uuid.UUID, Dict[str, Any]] = {}
        # Spend by Status
        status_map: Dict[str, Dict[str, Any]] = {}

        for po in pos:
            amt = Decimal(str(po.total_amount))

            # Supplier grouping
            sid = po.supplier_id
            if sid not in supp_map:
                supp_map[sid] = {
                    "supplier_id": sid,
                    "supplier_code": po.supplier.code if po.supplier else "",
                    "supplier_name": po.supplier.name if po.supplier else "",
                    "total_amount": Decimal("0.0"),
                    "po_count": 0,
                }
            supp_map[sid]["total_amount"] += amt
            supp_map[sid]["po_count"] += 1

            # Month grouping
            m_str = po.order_date.strftime("%Y-%m")
            if m_str not in month_map:
                month_map[m_str] = {"month": m_str, "total_amount": Decimal("0.0"), "po_count": 0}
            month_map[m_str]["total_amount"] += amt
            month_map[m_str]["po_count"] += 1

            # Status grouping
            st = po.status
            if st not in status_map:
                status_map[st] = {"status": st, "total_amount": Decimal("0.0"), "po_count": 0}
            status_map[st]["total_amount"] += amt
            status_map[st]["po_count"] += 1

            # Warehouse grouping (from items)
            for itm in po.items:
                wid = itm.warehouse_id
                item_amt = Decimal(str(itm.total_price))
                if wid not in wh_map:
                    wh_map[wid] = {
                        "warehouse_id": wid,
                        "warehouse_code": itm.warehouse.code if itm.warehouse else "",
                        "warehouse_name": itm.warehouse.name if itm.warehouse else "",
                        "total_amount": Decimal("0.0"),
                        "po_count": 0,
                    }
                wh_map[wid]["total_amount"] += item_amt
                wh_map[wid]["po_count"] += 1

        spend_by_supp = [SupplierSpendItem(**v) for v in sorted(supp_map.values(), key=lambda x: x["total_amount"], reverse=True)]
        spend_by_mon = [MonthlySpendItem(**v) for v in sorted(month_map.values(), key=lambda x: x["month"])]
        spend_by_wh = [WarehouseSpendItem(**v) for v in sorted(wh_map.values(), key=lambda x: x["total_amount"], reverse=True)]
        spend_by_st = [StatusSpendItem(**v) for v in sorted(status_map.values(), key=lambda x: x["total_amount"], reverse=True)]

        return ProcurementSpendAnalyticsResponse(
            total_spend=total_spend,
            spend_by_supplier=spend_by_supp,
            spend_by_month=spend_by_mon,
            spend_by_warehouse=spend_by_wh,
            spend_by_status=spend_by_st,
        )

    async def get_efficiency_metrics(
        self,
        db: AsyncSession,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> ProcurementEfficiencyMetricsResponse:
        # 1. RFQs & Quotations
        rfq_stmt = select(RFQ).options(selectinload(RFQ.invited_suppliers), selectinload(RFQ.quotations))
        if date_from:
            rfq_stmt = rfq_stmt.where(RFQ.created_at >= date_from)
        if date_to:
            rfq_stmt = rfq_stmt.where(RFQ.created_at <= date_to)
        rfq_res = await db.execute(rfq_stmt)
        rfqs = rfq_res.scalars().all()

        tot_rfqs = len(rfqs)
        tot_invitations = sum(len(r.invited_suppliers) for r in rfqs)
        tot_rfq_quotes = sum(len(r.quotations) for r in rfqs)

        # Total quotations overall
        sq_stmt = select(SupplierQuotation)
        if date_from:
            sq_stmt = sq_stmt.where(SupplierQuotation.quotation_date >= date_from)
        if date_to:
            sq_stmt = sq_stmt.where(SupplierQuotation.quotation_date <= date_to)
        sq_res = await db.execute(sq_stmt)
        all_quotes = sq_res.scalars().all()
        tot_quotes = len(all_quotes)
        approved_quotes = sum(1 for q in all_quotes if q.status == "Approved")

        # 2. Requisitions to PO conversion
        pr_stmt = select(PurchaseRequisition)
        if date_from:
            pr_stmt = pr_stmt.where(PurchaseRequisition.created_at >= date_from)
        if date_to:
            pr_stmt = pr_stmt.where(PurchaseRequisition.created_at <= date_to)
        pr_res = await db.execute(pr_stmt)
        prs = pr_res.scalars().all()
        tot_prs = len(prs)
        converted_prs = sum(1 for pr in prs if pr.status in ["Partially Fulfilled", "Fulfilled", "Approved"])

        # 3. PO completion & receiving
        po_stmt = select(PurchaseOrder).options(selectinload(PurchaseOrder.items))
        if date_from:
            po_stmt = po_stmt.where(PurchaseOrder.order_date >= date_from)
        if date_to:
            po_stmt = po_stmt.where(PurchaseOrder.order_date <= date_to)
        po_res = await db.execute(po_stmt)
        pos = po_res.scalars().all()

        tot_pos = len(pos)
        approved_pos = sum(1 for p in pos if p.status in ["Approved", "Partially Received", "Fully Received", "Closed"])
        fully_rec_pos = sum(1 for p in pos if p.status == "Fully Received")

        tot_ord_qty = Decimal("0.0")
        tot_rec_qty = Decimal("0.0")
        tot_ret_qty = Decimal("0.0")

        for p in pos:
            for itm in p.items:
                tot_ord_qty += Decimal(str(itm.quantity))
                tot_rec_qty += Decimal(str(itm.received_quantity))
                tot_ret_qty += Decimal(str(itm.returned_quantity))

        # Efficiency calculation
        rfq_part_rate = (
            Decimal(str(round((tot_rfq_quotes / tot_invitations * 100), 2)))
            if tot_invitations > 0
            else (Decimal("100.0") if tot_rfqs > 0 and tot_rfq_quotes > 0 else Decimal("0.0"))
        )
        avg_quotes_rfq = Decimal(str(round(tot_quotes / tot_rfqs, 2))) if tot_rfqs > 0 else Decimal("0.0")
        quote_award_ratio = Decimal(str(round(approved_quotes / tot_quotes * 100, 2))) if tot_quotes > 0 else Decimal("0.0")
        pr_po_conv_ratio = Decimal(str(round(converted_prs / tot_prs * 100, 2))) if tot_prs > 0 else Decimal("0.0")
        po_rec_comp_ratio = Decimal(str(round(fully_rec_pos / approved_pos * 100, 2))) if approved_pos > 0 else Decimal("0.0")
        ret_ratio = Decimal(str(round(tot_ret_qty / tot_rec_qty * 100, 2))) if tot_rec_qty > 0 else Decimal("0.0")

        return ProcurementEfficiencyMetricsResponse(
            rfq_participation_rate=rfq_part_rate,
            average_quotations_per_rfq=avg_quotes_rfq,
            quotation_to_award_ratio=quote_award_ratio,
            pr_to_po_conversion_ratio=pr_po_conv_ratio,
            po_to_receipt_completion_ratio=po_rec_comp_ratio,
            purchase_return_ratio=ret_ratio,
            total_rfqs=tot_rfqs,
            total_quotations=tot_quotes,
            total_pos=tot_pos,
            fully_received_pos=fully_rec_pos,
            total_ordered_quantity=tot_ord_qty,
            total_received_quantity=tot_rec_qty,
            total_returned_quantity=tot_ret_qty,
        )


class ProcurementAnalyticsService:
    """
    Executive Analytics Service providing cached dashboard telemetry and snapshot generation.
    """

    async def get_dashboard_summary(
        self,
        db: AsyncSession,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> ProcurementDashboardSummary:
        cache_key = f"procurement:dashboard:summary:{date_from}:{date_to}"
        cached = await redis_manager.get_json(cache_key)
        if cached:
            return ProcurementDashboardSummary(**cached)

        # 1. Total Spend
        spend_stmt = select(func.coalesce(func.sum(PurchaseOrder.total_amount), Decimal("0.0"))).where(
            PurchaseOrder.status.in_(["Approved", "Partially Received", "Fully Received", "Closed"])
        )
        if date_from:
            spend_stmt = spend_stmt.where(PurchaseOrder.order_date >= date_from)
        if date_to:
            spend_stmt = spend_stmt.where(PurchaseOrder.order_date <= date_to)

        spend_res = await db.execute(spend_stmt)
        tot_spend = Decimal(str(spend_res.scalar() or 0.0))

        # 2. Supplier Counts
        tot_supp_stmt = select(func.count(Supplier.id)).where(Supplier.is_deleted == False)
        tot_supp_res = await db.execute(tot_supp_stmt)
        tot_supp_cnt = tot_supp_res.scalar() or 0

        act_supp_stmt = select(func.count(Supplier.id)).where(Supplier.status == "Active").where(Supplier.is_deleted == False)
        act_supp_res = await db.execute(act_supp_stmt)
        act_supp_cnt = act_supp_res.scalar() or 0

        blk_supp_stmt = select(func.count(Supplier.id)).where(Supplier.status == "Blacklisted").where(Supplier.is_deleted == False)
        blk_supp_res = await db.execute(blk_supp_stmt)
        blk_supp_cnt = blk_supp_res.scalar() or 0

        # 3. Requisitions Counts
        open_req_stmt = select(func.count(PurchaseRequisition.id)).where(
            PurchaseRequisition.status.in_(["Draft", "Submitted", "Approved", "Partially Fulfilled"])
        )
        if date_from:
            open_req_stmt = open_req_stmt.where(PurchaseRequisition.created_at >= date_from)
        if date_to:
            open_req_stmt = open_req_stmt.where(PurchaseRequisition.created_at <= date_to)
        open_req_res = await db.execute(open_req_stmt)
        open_req_cnt = open_req_res.scalar() or 0

        sub_req_stmt = select(func.count(PurchaseRequisition.id)).where(PurchaseRequisition.status == "Submitted")
        if date_from:
            sub_req_stmt = sub_req_stmt.where(PurchaseRequisition.created_at >= date_from)
        if date_to:
            sub_req_stmt = sub_req_stmt.where(PurchaseRequisition.created_at <= date_to)
        sub_req_res = await db.execute(sub_req_stmt)
        sub_req_cnt = sub_req_res.scalar() or 0

        # 4. RFQ and Quotation Counts
        open_rfq_stmt = select(func.count(RFQ.id)).where(RFQ.status.in_(["Draft", "Issued"]))
        if date_from:
            open_rfq_stmt = open_rfq_stmt.where(RFQ.created_at >= date_from)
        if date_to:
            open_rfq_stmt = open_rfq_stmt.where(RFQ.created_at <= date_to)
        open_rfq_res = await db.execute(open_rfq_stmt)
        open_rfq_cnt = open_rfq_res.scalar() or 0

        sub_quot_stmt = select(func.count(SupplierQuotation.id)).where(SupplierQuotation.status == "Submitted")
        if date_from:
            sub_quot_stmt = sub_quot_stmt.where(SupplierQuotation.quotation_date >= date_from)
        if date_to:
            sub_quot_stmt = sub_quot_stmt.where(SupplierQuotation.quotation_date <= date_to)
        sub_quot_res = await db.execute(sub_quot_stmt)
        sub_quot_cnt = sub_quot_res.scalar() or 0

        app_quot_stmt = select(func.count(SupplierQuotation.id)).where(SupplierQuotation.status == "Approved")
        if date_from:
            app_quot_stmt = app_quot_stmt.where(SupplierQuotation.quotation_date >= date_from)
        if date_to:
            app_quot_stmt = app_quot_stmt.where(SupplierQuotation.quotation_date <= date_to)
        app_quot_res = await db.execute(app_quot_stmt)
        app_quot_cnt = app_quot_res.scalar() or 0

        # 5. PO Counts & Quantities
        open_po_stmt = select(func.count(PurchaseOrder.id)).where(
            PurchaseOrder.status.in_(["Submitted", "Approved", "Partially Received"])
        )
        if date_from:
            open_po_stmt = open_po_stmt.where(PurchaseOrder.order_date >= date_from)
        if date_to:
            open_po_stmt = open_po_stmt.where(PurchaseOrder.order_date <= date_to)
        open_po_res = await db.execute(open_po_stmt)
        open_po_cnt = open_po_res.scalar() or 0

        act_po_stmt = select(func.count(PurchaseOrder.id)).where(
            PurchaseOrder.status.in_(["Approved", "Partially Received"])
        )
        if date_from:
            act_po_stmt = act_po_stmt.where(PurchaseOrder.order_date >= date_from)
        if date_to:
            act_po_stmt = act_po_stmt.where(PurchaseOrder.order_date <= date_to)
        act_po_res = await db.execute(act_po_stmt)
        act_po_cnt = act_po_res.scalar() or 0

        disp_po_stmt = select(func.count(PurchaseOrder.id)).where(
            PurchaseOrder.status.in_(["Partially Received", "Fully Received"])
        )
        if date_from:
            disp_po_stmt = disp_po_stmt.where(PurchaseOrder.order_date >= date_from)
        if date_to:
            disp_po_stmt = disp_po_stmt.where(PurchaseOrder.order_date <= date_to)
        disp_po_res = await db.execute(disp_po_stmt)
        disp_po_cnt = disp_po_res.scalar() or 0

        part_po_stmt = select(func.count(PurchaseOrder.id)).where(PurchaseOrder.status == "Partially Received")
        if date_from:
            part_po_stmt = part_po_stmt.where(PurchaseOrder.order_date >= date_from)
        if date_to:
            part_po_stmt = part_po_stmt.where(PurchaseOrder.order_date <= date_to)
        part_po_res = await db.execute(part_po_stmt)
        part_po_cnt = part_po_res.scalar() or 0

        full_po_stmt = select(func.count(PurchaseOrder.id)).where(PurchaseOrder.status == "Fully Received")
        if date_from:
            full_po_stmt = full_po_stmt.where(PurchaseOrder.order_date >= date_from)
        if date_to:
            full_po_stmt = full_po_stmt.where(PurchaseOrder.order_date <= date_to)
        full_po_res = await db.execute(full_po_stmt)
        full_po_cnt = full_po_res.scalar() or 0

        sub_po_stmt = select(func.count(PurchaseOrder.id)).where(PurchaseOrder.status == "Submitted")
        if date_from:
            sub_po_stmt = sub_po_stmt.where(PurchaseOrder.order_date >= date_from)
        if date_to:
            sub_po_stmt = sub_po_stmt.where(PurchaseOrder.order_date <= date_to)
        sub_po_res = await db.execute(sub_po_stmt)
        sub_po_cnt = sub_po_res.scalar() or 0

        pending_approvals = sub_req_cnt + sub_po_cnt

        # 6. Quantities
        po_items_stmt = select(
            func.coalesce(func.sum(PurchaseOrderItem.quantity), Decimal("0.0")).label("ord_qty"),
            func.coalesce(func.sum(PurchaseOrderItem.received_quantity), Decimal("0.0")).label("rec_qty"),
            func.coalesce(func.sum(PurchaseOrderItem.returned_quantity), Decimal("0.0")).label("ret_qty"),
        ).join(PurchaseOrder, PurchaseOrderItem.purchase_order_id == PurchaseOrder.id)
        if date_from:
            po_items_stmt = po_items_stmt.where(PurchaseOrder.order_date >= date_from)
        if date_to:
            po_items_stmt = po_items_stmt.where(PurchaseOrder.order_date <= date_to)

        po_items_res = await db.execute(po_items_stmt)
        qty_row = po_items_res.one()
        tot_ord_qty = Decimal(str(qty_row.ord_qty or 0.0))
        tot_rec_qty = Decimal(str(qty_row.rec_qty or 0.0))
        tot_ret_qty = Decimal(str(qty_row.ret_qty or 0.0))

        # 7. Delayed Orders Count
        now = datetime.now(timezone.utc)
        delay_stmt = (
            select(func.count(PurchaseOrder.id))
            .where(PurchaseOrder.status.in_(["Approved", "Partially Received"]))
            .where(PurchaseOrder.expected_delivery_date.isnot(None))
            .where(PurchaseOrder.expected_delivery_date < now)
        )
        if date_from:
            delay_stmt = delay_stmt.where(PurchaseOrder.order_date >= date_from)
        if date_to:
            delay_stmt = delay_stmt.where(PurchaseOrder.order_date <= date_to)
        delay_res = await db.execute(delay_stmt)
        delay_cnt = delay_res.scalar() or 0

        # 8. Top Vendors
        top_v_stmt = (
            select(
                Supplier.id.label("supplier_id"),
                Supplier.name.label("supplier_name"),
                func.coalesce(func.sum(PurchaseOrder.total_amount), Decimal("0.0")).label("total_spend"),
                func.count(PurchaseOrder.id).label("po_count"),
            )
            .join(PurchaseOrder, Supplier.id == PurchaseOrder.supplier_id)
            .where(PurchaseOrder.status.in_(["Approved", "Partially Received", "Fully Received", "Closed"]))
            .group_by(Supplier.id, Supplier.name)
            .order_by(func.sum(PurchaseOrder.total_amount).desc())
            .limit(5)
        )
        if date_from:
            top_v_stmt = top_v_stmt.where(PurchaseOrder.order_date >= date_from)
        if date_to:
            top_v_stmt = top_v_stmt.where(PurchaseOrder.order_date <= date_to)
        top_v_res = await db.execute(top_v_stmt)
        top_vendors = [
            {
                "supplier_id": str(r.supplier_id),
                "supplier_name": r.supplier_name,
                "total_spend": float(r.total_spend),
                "po_count": r.po_count,
            }
            for r in top_v_res.all()
        ]

        summary = ProcurementDashboardSummary(
            total_purchase_spend=tot_spend,
            open_po_count=open_po_cnt,
            open_requisitions_count=open_req_cnt,
            active_suppliers_count=act_supp_cnt,
            delayed_orders_count=delay_cnt,
            total_suppliers=tot_supp_cnt,
            active_suppliers=act_supp_cnt,
            blacklisted_suppliers=blk_supp_cnt,
            open_requisitions=open_req_cnt,
            submitted_requisitions=sub_req_cnt,
            pending_approvals=pending_approvals,
            open_rfqs=open_rfq_cnt,
            submitted_quotations=sub_quot_cnt,
            approved_quotations=app_quot_cnt,
            active_purchase_orders=act_po_cnt,
            dispatched_purchase_orders=disp_po_cnt,
            partially_received_pos=part_po_cnt,
            fully_received_pos=full_po_cnt,
            total_ordered_quantity=tot_ord_qty,
            total_received_quantity=tot_rec_qty,
            total_returned_quantity=tot_ret_qty,
            spend_by_department=[],
            top_vendors=top_vendors,
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
