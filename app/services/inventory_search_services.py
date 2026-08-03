from typing import Any, Dict, List
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.batch import Batch
from app.models.lot import Lot
from app.models.product import Product
from app.models.serial_number import SerialNumber
from app.models.storage_location import StorageLocation
from app.models.warehouse import Warehouse
from app.schemas.inventory_advanced import GlobalSearchResponse, SearchResultItem


class InventorySearchService:
    async def global_search(self, db: AsyncSession, query: str, limit: int = 50) -> GlobalSearchResponse:
        search_pattern = f"%{query.strip()}%"
        results: List[SearchResultItem] = []

        # 1. Search Products (SKU, Barcode, Name)
        prod_stmt = (
            select(Product)
            .where(
                or_(
                    Product.sku.ilike(search_pattern),
                    Product.barcode.ilike(search_pattern),
                    Product.name.ilike(search_pattern),
                )
            )
            .limit(limit)
        )
        prod_res = await db.execute(prod_stmt)
        for p in prod_res.scalars().all():
            results.append(
                SearchResultItem(
                    entity_type="Product",
                    entity_id=p.id,
                    title=p.name,
                    subtitle=f"SKU: {p.sku} | Barcode: {p.barcode or 'N/A'}",
                    sku_or_code=p.sku,
                    details={"status": p.status, "type": p.product_type},
                )
            )

        # 2. Search Batches (Batch Number, Supplier Ref)
        batch_stmt = (
            select(Batch)
            .where(
                or_(
                    Batch.batch_number.ilike(search_pattern),
                    Batch.supplier_batch_ref.ilike(search_pattern),
                )
            )
            .limit(limit)
        )
        batch_res = await db.execute(batch_stmt)
        for b in batch_res.scalars().all():
            results.append(
                SearchResultItem(
                    entity_type="Batch",
                    entity_id=b.id,
                    title=f"Batch: {b.batch_number}",
                    subtitle=f"Status: {b.status} | Qty: {b.current_quantity}",
                    sku_or_code=b.batch_number,
                    details={"status": b.status, "qty": float(b.current_quantity)},
                )
            )

        # 3. Search Serial Numbers
        sn_stmt = (
            select(SerialNumber)
            .where(SerialNumber.serial_number.ilike(search_pattern))
            .limit(limit)
        )
        sn_res = await db.execute(sn_stmt)
        for s in sn_res.scalars().all():
            results.append(
                SearchResultItem(
                    entity_type="SerialNumber",
                    entity_id=s.id,
                    title=f"Serial: {s.serial_number}",
                    subtitle=f"Status: {s.status}",
                    sku_or_code=s.serial_number,
                    details={"status": s.status},
                )
            )

        # 4. Search Lots
        lot_stmt = (
            select(Lot)
            .where(
                or_(
                    Lot.lot_number.ilike(search_pattern),
                    Lot.production_lot.ilike(search_pattern),
                    Lot.supplier_lot.ilike(search_pattern),
                )
            )
            .limit(limit)
        )
        lot_res = await db.execute(lot_stmt)
        for l in lot_res.scalars().all():
            results.append(
                SearchResultItem(
                    entity_type="Lot",
                    entity_id=l.id,
                    title=f"Lot: {l.lot_number}",
                    subtitle=f"Prod Lot: {l.production_lot or 'N/A'}",
                    sku_or_code=l.lot_number,
                    details={},
                )
            )

        # 5. Search Warehouses
        wh_stmt = (
            select(Warehouse)
            .where(
                or_(
                    Warehouse.code.ilike(search_pattern),
                    Warehouse.name.ilike(search_pattern),
                )
            )
            .limit(limit)
        )
        wh_res = await db.execute(wh_stmt)
        for w in wh_res.scalars().all():
            results.append(
                SearchResultItem(
                    entity_type="Warehouse",
                    entity_id=w.id,
                    title=w.name,
                    subtitle=f"Code: {w.code}",
                    sku_or_code=w.code,
                    details={"is_active": w.is_active},
                )
            )

        # 6. Search Storage Locations
        loc_stmt = (
            select(StorageLocation)
            .where(
                or_(
                    StorageLocation.code.ilike(search_pattern),
                    StorageLocation.name.ilike(search_pattern),
                )
            )
            .limit(limit)
        )
        loc_res = await db.execute(loc_stmt)
        for loc in loc_res.scalars().all():
            results.append(
                SearchResultItem(
                    entity_type="StorageLocation",
                    entity_id=loc.id,
                    title=loc.name,
                    subtitle=f"Code: {loc.code} | Type: {loc.location_type}",
                    sku_or_code=loc.code,
                    details={"type": loc.location_type},
                )
            )

        return GlobalSearchResponse(
            query=query,
            total_results=len(results),
            results=results[:limit],
        )


inventory_search_service = InventorySearchService()
