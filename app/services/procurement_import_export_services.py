import csv
import io
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.base import ValidationException
from app.models.purchase_order import PurchaseOrder
from app.models.supplier import Supplier
from app.schemas.procurement import ProcurementImportResult


class ProcurementImportExportService:
    """
    Service responsible for streaming CSV export and bulk CSV import of Procurement domain entities.
    """
    async def export_to_csv(self, db: AsyncSession, entity_type: str) -> str:
        output = io.StringIO()
        writer = csv.writer(output)

        if entity_type == "suppliers":
            writer.writerow(["Code", "Name", "Tax ID", "GST/VAT", "Payment Terms", "Currency", "Status", "Total Spend"])
            stmt = select(Supplier).where(Supplier.is_deleted == False)
            res = await db.execute(stmt)
            for s in res.scalars().all():
                writer.writerow(
                    [s.code, s.name, s.tax_id or "", s.gst_vat_number or "", s.payment_terms, s.currency, s.status, float(s.total_spend)]
                )

        elif entity_type == "purchase_orders":
            writer.writerow(["PO Number", "Origin Type", "Supplier ID", "Order Date", "Status", "Total Amount"])
            stmt = select(PurchaseOrder)
            res = await db.execute(stmt)
            for po in res.scalars().all():
                writer.writerow(
                    [po.po_number, po.origin_type, str(po.supplier_id), po.order_date.isoformat(), po.status, float(po.total_amount)]
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
