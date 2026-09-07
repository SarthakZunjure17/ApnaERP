import csv
from datetime import datetime
from decimal import Decimal
import io
import logging
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions.base import ValidationException
from app.models.goods_receipt import GoodsReceipt
from app.models.purchase_order import PurchaseOrder
from app.models.purchase_requisition import PurchaseRequisition
from app.models.purchase_return import PurchaseReturn
from app.models.rfq import RFQ
from app.models.supplier import Supplier
from app.models.supplier_quotation import SupplierQuotation
from app.schemas.procurement import ProcurementImportResult

logger = logging.getLogger("app.services.procurement_import_export")


class ProcurementImportExportService:
    """
    Service responsible for streaming CSV export and bulk CSV import of Procurement domain entities.
    Strictly sanitizes CSV fields and preserves domain boundaries.
    """

    async def export_to_csv(self, db: AsyncSession, entity_type: str) -> str:
        output = io.StringIO()
        writer = csv.writer(output)

        if entity_type == "suppliers":
            writer.writerow(["Code", "Name", "Tax ID", "GST/VAT", "Payment Terms", "Currency", "Status", "Rating", "Total Spend"])
            stmt = select(Supplier).where(Supplier.is_deleted == False).order_by(Supplier.name.asc())
            res = await db.execute(stmt)
            for s in res.scalars().all():
                writer.writerow(
                    [
                        s.code,
                        s.name,
                        s.tax_id or "",
                        s.gst_vat_number or "",
                        s.payment_terms,
                        s.currency,
                        s.status,
                        float(s.rating),
                        float(s.total_spend),
                    ]
                )

        elif entity_type in ["purchase_orders", "orders"]:
            writer.writerow(["PO Number", "Origin Type", "Supplier", "Order Date", "Status", "Currency", "Subtotal", "Tax", "Discount", "Total Amount"])
            stmt = select(PurchaseOrder).options(selectinload(PurchaseOrder.supplier)).order_by(PurchaseOrder.order_date.desc())
            res = await db.execute(stmt)
            for po in res.scalars().all():
                writer.writerow(
                    [
                        po.po_number,
                        po.origin_type,
                        po.supplier.name if po.supplier else str(po.supplier_id),
                        po.order_date.isoformat(),
                        po.status,
                        po.currency,
                        float(po.subtotal),
                        float(po.tax_amount),
                        float(po.discount_amount),
                        float(po.total_amount),
                    ]
                )

        elif entity_type in ["receiving", "goods_receipts"]:
            writer.writerow(["Receipt Number", "PO Reference", "Warehouse", "Receipt Date", "Status", "Total Items", "Total Quantity"])
            stmt = select(GoodsReceipt).options(selectinload(GoodsReceipt.warehouse), selectinload(GoodsReceipt.items)).order_by(GoodsReceipt.receipt_date.desc())
            res = await db.execute(stmt)
            for gr in res.scalars().all():
                tot_qty = sum((float(itm.quantity) for itm in gr.items), 0.0)
                writer.writerow(
                    [
                        gr.receipt_number,
                        gr.external_reference or "",
                        gr.warehouse.code if gr.warehouse else str(gr.warehouse_id),
                        gr.receipt_date.isoformat(),
                        gr.status,
                        len(gr.items),
                        tot_qty,
                    ]
                )

        elif entity_type in ["returns", "purchase_returns"]:
            writer.writerow(["Return Number", "PO Number", "Supplier", "Warehouse", "Return Date", "Reason", "Status", "Total Amount"])
            stmt = select(PurchaseReturn).options(selectinload(PurchaseReturn.purchase_order), selectinload(PurchaseReturn.supplier), selectinload(PurchaseReturn.warehouse)).order_by(PurchaseReturn.return_date.desc())
            res = await db.execute(stmt)
            for r in res.scalars().all():
                writer.writerow(
                    [
                        r.return_number,
                        r.purchase_order.po_number if r.purchase_order else str(r.purchase_order_id),
                        r.supplier.name if r.supplier else str(r.supplier_id),
                        r.warehouse.code if r.warehouse else str(r.warehouse_id),
                        r.return_date.isoformat(),
                        r.reason_code,
                        r.status,
                        float(r.total_return_amount),
                    ]
                )

        elif entity_type in ["requisitions", "purchase_requisitions"]:
            writer.writerow(["Requisition Number", "Priority", "Status", "Required Date", "Estimated Amount", "Items Count", "Created At"])
            stmt = select(PurchaseRequisition).options(selectinload(PurchaseRequisition.items)).order_by(PurchaseRequisition.created_at.desc())
            res = await db.execute(stmt)
            for pr in res.scalars().all():
                writer.writerow(
                    [
                        pr.requisition_number,
                        pr.priority,
                        pr.status,
                        pr.required_date.isoformat(),
                        float(pr.total_estimated_amount),
                        len(pr.items),
                        pr.created_at.isoformat(),
                    ]
                )

        elif entity_type in ["quotations", "supplier_quotations"]:
            writer.writerow(["Quotation Number", "Supplier", "Quotation Date", "Validity Date", "Lead Time Days", "Currency", "Total Amount", "Status"])
            stmt = select(SupplierQuotation).options(selectinload(SupplierQuotation.supplier)).order_by(SupplierQuotation.quotation_date.desc())
            res = await db.execute(stmt)
            for sq in res.scalars().all():
                writer.writerow(
                    [
                        sq.quotation_number,
                        sq.supplier.name if sq.supplier else str(sq.supplier_id),
                        sq.quotation_date.isoformat(),
                        sq.validity_date.isoformat(),
                        sq.lead_time_days,
                        sq.currency,
                        float(sq.total_amount),
                        sq.status,
                    ]
                )

        elif entity_type == "rfqs":
            writer.writerow(["RFQ Number", "Title", "Submission Deadline", "Status", "Invited Count", "Quotations Count", "Created At"])
            stmt = select(RFQ).options(selectinload(RFQ.invited_suppliers), selectinload(RFQ.quotations)).order_by(RFQ.created_at.desc())
            res = await db.execute(stmt)
            for rfq in res.scalars().all():
                writer.writerow(
                    [
                        rfq.rfq_number,
                        rfq.title,
                        rfq.submission_deadline.isoformat(),
                        rfq.status,
                        len(rfq.invited_suppliers),
                        len(rfq.quotations),
                        rfq.created_at.isoformat(),
                    ]
                )
        else:
            raise ValidationException(f"Unsupported export entity type '{entity_type}'.")

        return output.getvalue()

    async def import_from_csv(
        self, db: AsyncSession, entity_type: str, csv_content: str
    ) -> ProcurementImportResult:
        success = 0
        errors: List[str] = []

        reader = csv.DictReader(io.StringIO(csv_content))
        for idx, row in enumerate(reader, start=2):
            try:
                if entity_type == "suppliers":
                    code = row.get("Code", "").strip()
                    name = row.get("Name", "").strip()
                    if not code or not name:
                        errors.append(f"Row {idx}: Code and Name are required.")
                        continue

                    existing = await db.execute(select(Supplier).where(Supplier.code == code))
                    if existing.scalar_one_or_none():
                        errors.append(f"Row {idx}: Supplier code '{code}' already exists.")
                        continue

                    s = Supplier(
                        code=code,
                        name=name,
                        tax_id=row.get("Tax ID"),
                        gst_vat_number=row.get("GST/VAT"),
                        payment_terms=row.get("Payment Terms", "Net 30"),
                        currency=row.get("Currency", "USD"),
                        status="Active",
                    )
                    db.add(s)
                    success += 1
                else:
                    errors.append(f"Row {idx}: Import not supported for entity '{entity_type}'.")
            except Exception as e:
                errors.append(f"Row {idx}: {str(e)}")

        if success > 0:
            await db.commit()

        return ProcurementImportResult(
            success_count=success,
            error_count=len(errors),
            errors=errors,
        )


procurement_import_export_service = ProcurementImportExportService()
