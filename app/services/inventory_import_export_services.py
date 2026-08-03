import csv
import io
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.base import ValidationException

from app.models.batch import Batch
from app.models.product import Product
from app.models.serial_number import SerialNumber
from app.models.stock_balance import StockBalance
from app.schemas.inventory_advanced import ImportResult


class InventoryImportExportService:
    async def export_to_csv(self, db: AsyncSession, entity_type: str) -> str:
        output = io.StringIO()
        writer = csv.writer(output)

        ent_type = entity_type.lower()
        if ent_type == "products":
            writer.writerow(["ID", "SKU", "Name", "ProductType", "Status", "CreatedAt"])
            stmt = select(Product)
            res = await db.execute(stmt)
            for p in res.scalars().all():
                writer.writerow([str(p.id), p.sku, p.name, p.product_type, p.status, p.created_at.isoformat()])

        elif ent_type == "stock_balances":
            writer.writerow(["ProductID", "WarehouseID", "AvailableQty", "ReservedQty", "UpdatedAt"])
            stmt = select(StockBalance)
            res = await db.execute(stmt)
            for b in res.scalars().all():
                writer.writerow([str(b.product_id), str(b.warehouse_id), str(b.available_quantity), str(b.reserved_quantity), b.updated_at.isoformat()])

        elif ent_type == "batches":
            writer.writerow(["ID", "BatchNumber", "ProductID", "Quantity", "Status", "ExpiryDate"])
            stmt = select(Batch)
            res = await db.execute(stmt)
            for b in res.scalars().all():
                writer.writerow([str(b.id), b.batch_number, str(b.product_id), str(b.current_quantity), b.status, b.expiry_date.isoformat() if b.expiry_date else ""])

        elif ent_type == "serials":
            writer.writerow(["ID", "SerialNumber", "ProductID", "WarehouseID", "Status"])
            stmt = select(SerialNumber)
            res = await db.execute(stmt)
            for s in res.scalars().all():
                writer.writerow([str(s.id), s.serial_number, str(s.product_id), str(s.warehouse_id or ""), s.status])

        else:
            raise ValidationException(f"Unsupported entity type '{entity_type}' for CSV export.")

        return output.getvalue()

    async def import_from_csv(self, db: AsyncSession, entity_type: str, csv_content: str) -> ImportResult:
        ent_type = entity_type.lower()
        errors: List[str] = []
        imported_count = 0

        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)

        if ent_type == "batches":
            for idx, row in enumerate(rows, start=1):
                try:
                    b_num = row.get("BatchNumber") or row.get("batch_number")
                    p_id = row.get("ProductID") or row.get("product_id")
                    qty = float(row.get("Quantity") or row.get("quantity") or 0)
                    if not b_num or not p_id:
                        errors.append(f"Row {idx}: BatchNumber and ProductID are required.")
                        continue

                    batch = Batch(
                        batch_number=b_num.strip(),
                        product_id=uuid.UUID(p_id.strip()),
                        current_quantity=qty,
                        status="Active",
                    )
                    db.add(batch)
                    imported_count += 1
                except Exception as exc:
                    errors.append(f"Row {idx}: {str(exc)}")

            await db.commit()

        elif ent_type == "serials":
            for idx, row in enumerate(rows, start=1):
                try:
                    s_num = row.get("SerialNumber") or row.get("serial_number")
                    p_id = row.get("ProductID") or row.get("product_id")
                    if not s_num or not p_id:
                        errors.append(f"Row {idx}: SerialNumber and ProductID are required.")
                        continue

                    serial = SerialNumber(
                        serial_number=s_num.strip(),
                        product_id=uuid.UUID(p_id.strip()),
                        status="Available",
                    )
                    db.add(serial)
                    imported_count += 1
                except Exception as exc:
                    errors.append(f"Row {idx}: {str(exc)}")

            await db.commit()

        else:
            raise ValidationException(f"Unsupported entity type '{entity_type}' for CSV import.")

        return ImportResult(
            entity_type=entity_type,
            total_records=len(rows),
            imported_count=imported_count,
            failed_count=len(errors),
            errors=errors,
        )


inventory_import_export_service = InventoryImportExportService()
