from typing import Any, Dict, List, Optional
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.purchase_order import PurchaseOrder
from app.models.purchase_requisition import PurchaseRequisition
from app.models.rfq import RFQ
from app.models.supplier import Supplier
from app.models.supplier_quotation import SupplierQuotation
from app.schemas.procurement import GlobalProcurementSearchResponse


class ProcurementSearchService:
    """
    Unified multi-field global search service for Procurement domain entities.
    """
    async def global_search(
        self, db: AsyncSession, query: str, limit: int = 20
    ) -> GlobalProcurementSearchResponse:
        search_pattern = f"%{query.strip()}%"

        # 1. Suppliers
        s_stmt = (
            select(Supplier)
            .where(Supplier.is_deleted == False)
            .where(
                or_(
                    Supplier.code.ilike(search_pattern),
                    Supplier.name.ilike(search_pattern),
                    Supplier.gst_vat_number.ilike(search_pattern),
                )
            )
            .limit(limit)
        )
        s_res = await db.execute(s_stmt)
        suppliers = [
            {"id": str(s.id), "code": s.code, "name": s.name, "status": s.status} for s in s_res.scalars().all()
        ]

        # 2. Purchase Orders
        po_stmt = (
            select(PurchaseOrder)
            .where(
                or_(
                    PurchaseOrder.po_number.ilike(search_pattern),
                    PurchaseOrder.payment_terms.ilike(search_pattern),
                )
            )
            .limit(limit)
        )
        po_res = await db.execute(po_stmt)
        pos = [
            {
                "id": str(po.id),
                "po_number": po.po_number,
                "status": po.status,
                "total_amount": float(po.total_amount),
            }
            for po in po_res.scalars().all()
        ]

        # 3. RFQs
        rfq_stmt = (
            select(RFQ)
            .where(or_(RFQ.rfq_number.ilike(search_pattern), RFQ.title.ilike(search_pattern)))
            .limit(limit)
        )
        rfq_res = await db.execute(rfq_stmt)
        rfqs = [
            {"id": str(r.id), "rfq_number": r.rfq_number, "title": r.title, "status": r.status}
            for r in rfq_res.scalars().all()
        ]

        # 4. Supplier Quotations
        sq_stmt = (
            select(SupplierQuotation)
            .where(SupplierQuotation.quotation_number.ilike(search_pattern))
            .limit(limit)
        )
        sq_res = await db.execute(sq_stmt)
        sqs = [
            {
                "id": str(q.id),
                "quotation_number": q.quotation_number,
                "status": q.status,
                "total_amount": float(q.total_amount),
            }
            for q in sq_res.scalars().all()
        ]

        # 5. Purchase Requisitions
        pr_stmt = (
            select(PurchaseRequisition)
            .where(PurchaseRequisition.requisition_number.ilike(search_pattern))
            .limit(limit)
        )
        pr_res = await db.execute(pr_stmt)
        prs = [
            {"id": str(p.id), "requisition_number": p.requisition_number, "status": p.status, "priority": p.priority}
            for p in pr_res.scalars().all()
        ]

        return GlobalProcurementSearchResponse(
            query=query,
            suppliers=suppliers,
            purchase_orders=pos,
            rfqs=rfqs,
            quotations=sqs,
            requisitions=prs,
        )


procurement_search_service = ProcurementSearchService()
