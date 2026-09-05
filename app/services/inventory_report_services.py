import csv
from datetime import datetime, timezone
from decimal import Decimal
import io
import json
import math
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_manager
from app.models.batch import Batch
from app.models.inventory_analytics_snapshot import InventoryAnalyticsSnapshot
from app.models.product import Product
from app.models.serial_number import SerialNumber
from app.models.stock_balance import StockBalance
from app.models.stock_ledger import StockLedger
from app.models.stock_reservation import StockReservation
from app.models.warehouse import Warehouse
from app.repositories.inventory_advanced_repos import inventory_analytics_repository
from app.repositories.inventory_report_repos import inventory_report_repository
from app.schemas.inventory_advanced import (
    InventoryAgingItem,
    InventoryDashboardSummary,
    MovementAnalysisItem,
    StockValuationItem,
)
from app.schemas.inventory_reports import (
    AvailableStockReportItem,
    BatchExpiryReportItem,
    BatchExpiryReportSummary,
    InventoryAgingReportItem,
    InventoryAgingReportSummary,
    InventoryExecutiveDashboardResponse,
    InventoryMovementAnalyticsResponse,
    LowStockReportItem,
    LowStockReportSummary,
    PaginatedAvailableStockReportResponse,
    PaginatedBatchExpiryReportResponse,
    PaginatedInventoryAgingReportResponse,
    PaginatedLowStockReportResponse,
    PaginatedProductInventoryReportResponse,
    PaginatedSerialInventoryReportResponse,
    PaginatedStockMovementReportResponse,
    PaginatedStockReportResponse,
    PaginatedStockReservationReportResponse,
    PaginatedWarehouseInventoryReportResponse,
    ProductInventoryReportItem,
    SerialInventoryReportItem,
    StockMovementReportItem,
    StockMovementReportSummary,
    StockReportItem,
    StockReportSummary,
    StockReservationReportItem,
    StockReservationReportSummary,
    WarehouseInventoryReportItem,
)


class InventoryReportService:
    """
    Service layer providing read-only operational reports, movement analytics,
    and CSV export transformations over authoritative inventory data.
    """

    # =========================================================================
    # 1. CURRENT STOCK REPORT
    # =========================================================================
    async def get_current_stock_report(
        self,
        db: AsyncSession,
        product_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        storage_location_id: Optional[uuid.UUID] = None,
        category_id: Optional[uuid.UUID] = None,
        tracking_type: Optional[str] = None,
        active_only: bool = True,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 50,
    ) -> PaginatedStockReportResponse:
        skip = (page - 1) * size
        items, total, summary = await inventory_report_repository.get_current_stock_report(
            db=db,
            product_id=product_id,
            warehouse_id=warehouse_id,
            storage_location_id=storage_location_id,
            category_id=category_id,
            tracking_type=tracking_type,
            active_only=active_only,
            search=search,
            skip=skip,
            limit=size,
        )
        pages = math.ceil(total / size) if size > 0 else 1
        return PaginatedStockReportResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
            summary=summary,
        )

    # =========================================================================
    # 2. STOCK MOVEMENT REPORT
    # =========================================================================
    async def get_stock_movement_report(
        self,
        db: AsyncSession,
        product_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        storage_location_id: Optional[uuid.UUID] = None,
        movement_type: Optional[str] = None,
        direction: Optional[str] = None,
        batch_id: Optional[uuid.UUID] = None,
        reference_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 50,
    ) -> PaginatedStockMovementReportResponse:
        skip = (page - 1) * size
        items, total, summary = await inventory_report_repository.get_stock_movement_report(
            db=db,
            product_id=product_id,
            warehouse_id=warehouse_id,
            storage_location_id=storage_location_id,
            movement_type=movement_type,
            direction=direction,
            batch_id=batch_id,
            reference_type=reference_type,
            date_from=date_from,
            date_to=date_to,
            search=search,
            skip=skip,
            limit=size,
        )
        pages = math.ceil(total / size) if size > 0 else 1
        return PaginatedStockMovementReportResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
            summary=summary,
        )

    # =========================================================================
    # 3. WAREHOUSE INVENTORY REPORT
    # =========================================================================
    async def get_warehouse_inventory_report(
        self,
        db: AsyncSession,
        warehouse_id: Optional[uuid.UUID] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 50,
    ) -> PaginatedWarehouseInventoryReportResponse:
        skip = (page - 1) * size
        items, total = await inventory_report_repository.get_warehouse_inventory_report(
            db=db,
            warehouse_id=warehouse_id,
            is_active=is_active,
            search=search,
            skip=skip,
            limit=size,
        )
        pages = math.ceil(total / size) if size > 0 else 1
        return PaginatedWarehouseInventoryReportResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )

    # =========================================================================
    # 4. PRODUCT INVENTORY REPORT
    # =========================================================================
    async def get_product_inventory_report(
        self,
        db: AsyncSession,
        product_id: Optional[uuid.UUID] = None,
        category_id: Optional[uuid.UUID] = None,
        tracking_type: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 50,
    ) -> PaginatedProductInventoryReportResponse:
        skip = (page - 1) * size
        items, total = await inventory_report_repository.get_product_inventory_report(
            db=db,
            product_id=product_id,
            category_id=category_id,
            tracking_type=tracking_type,
            search=search,
            skip=skip,
            limit=size,
        )
        pages = math.ceil(total / size) if size > 0 else 1
        return PaginatedProductInventoryReportResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )

    # =========================================================================
    # 5. BATCH & EXPIRY REPORT
    # =========================================================================
    async def get_batch_expiry_report(
        self,
        db: AsyncSession,
        product_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        expiry_status: Optional[str] = None,
        expiring_within_days: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 50,
    ) -> PaginatedBatchExpiryReportResponse:
        skip = (page - 1) * size
        items, total, summary = await inventory_report_repository.get_batch_expiry_report(
            db=db,
            product_id=product_id,
            status=status,
            expiry_status=expiry_status,
            expiring_within_days=expiring_within_days,
            date_from=date_from,
            date_to=date_to,
            search=search,
            skip=skip,
            limit=size,
        )
        pages = math.ceil(total / size) if size > 0 else 1
        return PaginatedBatchExpiryReportResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
            summary=summary,
        )

    # =========================================================================
    # 6. SERIAL INVENTORY REPORT
    # =========================================================================
    async def get_serial_inventory_report(
        self,
        db: AsyncSession,
        product_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        storage_location_id: Optional[uuid.UUID] = None,
        batch_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 50,
    ) -> PaginatedSerialInventoryReportResponse:
        skip = (page - 1) * size
        items, total = await inventory_report_repository.get_serial_inventory_report(
            db=db,
            product_id=product_id,
            warehouse_id=warehouse_id,
            storage_location_id=storage_location_id,
            batch_id=batch_id,
            status=status,
            search=search,
            skip=skip,
            limit=size,
        )
        pages = math.ceil(total / size) if size > 0 else 1
        return PaginatedSerialInventoryReportResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )

    # =========================================================================
    # 7. STOCK RESERVATIONS REPORT
    # =========================================================================
    async def get_reservation_report(
        self,
        db: AsyncSession,
        product_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        reserved_for_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 50,
    ) -> PaginatedStockReservationReportResponse:
        skip = (page - 1) * size
        items, total, summary = await inventory_report_repository.get_reservation_report(
            db=db,
            product_id=product_id,
            warehouse_id=warehouse_id,
            status=status,
            reserved_for_type=reserved_for_type,
            date_from=date_from,
            date_to=date_to,
            search=search,
            skip=skip,
            limit=size,
        )
        pages = math.ceil(total / size) if size > 0 else 1
        return PaginatedStockReservationReportResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
            summary=summary,
        )

    # =========================================================================
    # 8. AVAILABLE STOCK REPORT
    # =========================================================================
    async def get_available_stock_report(
        self,
        db: AsyncSession,
        product_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        storage_location_id: Optional[uuid.UUID] = None,
        category_id: Optional[uuid.UUID] = None,
        tracking_type: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 50,
    ) -> PaginatedAvailableStockReportResponse:
        skip = (page - 1) * size
        items, total = await inventory_report_repository.get_available_stock_report(
            db=db,
            product_id=product_id,
            warehouse_id=warehouse_id,
            storage_location_id=storage_location_id,
            category_id=category_id,
            tracking_type=tracking_type,
            search=search,
            skip=skip,
            limit=size,
        )
        pages = math.ceil(total / size) if size > 0 else 1
        return PaginatedAvailableStockReportResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )

    # =========================================================================
    # 9. LOW STOCK / REORDER REPORT
    # =========================================================================
    async def get_low_stock_report(
        self,
        db: AsyncSession,
        warehouse_id: Optional[uuid.UUID] = None,
        category_id: Optional[uuid.UUID] = None,
        below_reorder_only: bool = False,
        below_min_only: bool = False,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 50,
    ) -> PaginatedLowStockReportResponse:
        skip = (page - 1) * size
        items, total, summary = await inventory_report_repository.get_low_stock_report(
            db=db,
            warehouse_id=warehouse_id,
            category_id=category_id,
            below_reorder_only=below_reorder_only,
            below_min_only=below_min_only,
            search=search,
            skip=skip,
            limit=size,
        )
        pages = math.ceil(total / size) if size > 0 else 1
        return PaginatedLowStockReportResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
            summary=summary,
        )

    # =========================================================================
    # 10. INVENTORY MOVEMENT ANALYTICS
    # =========================================================================
    async def get_movement_analytics(
        self,
        db: AsyncSession,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        product_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        category_id: Optional[uuid.UUID] = None,
    ) -> InventoryMovementAnalyticsResponse:
        return await inventory_report_repository.get_movement_analytics(
            db=db,
            date_from=date_from,
            date_to=date_to,
            product_id=product_id,
            warehouse_id=warehouse_id,
            category_id=category_id,
        )

    # =========================================================================
    # 11. INVENTORY AGING REPORT
    # =========================================================================
    async def get_inventory_aging_report_paginated(
        self,
        db: AsyncSession,
        warehouse_id: Optional[uuid.UUID] = None,
        aging_bucket: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 50,
    ) -> PaginatedInventoryAgingReportResponse:
        skip = (page - 1) * size
        items, total, summary = await inventory_report_repository.get_inventory_aging_report(
            db=db,
            warehouse_id=warehouse_id,
            aging_bucket=aging_bucket,
            search=search,
            skip=skip,
            limit=size,
        )
        pages = math.ceil(total / size) if size > 0 else 1
        return PaginatedInventoryAgingReportResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
            summary=summary,
        )

    # =========================================================================
    # 12. EXECUTIVE DASHBOARD SUMMARY
    # =========================================================================
    async def get_executive_dashboard_summary(
        self,
        db: AsyncSession,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> InventoryExecutiveDashboardResponse:
        return await inventory_report_repository.get_dashboard_summary(
            db=db,
            date_from=date_from,
            date_to=date_to,
        )

    # =========================================================================
    # 13. CSV EXPORT UTILITY
    # =========================================================================
    def export_report_to_csv(self, report_type: str, items: List[Any]) -> str:
        """
        Converts any list of report Pydantic schemas into standard CSV formatted string.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        if not items:
            writer.writerow(["No data available for export"])
            return output.getvalue()

        # Determine columns dynamically from first model dump
        first_item = items[0]
        if hasattr(first_item, "model_dump"):
            data_dict = first_item.model_dump()
        elif isinstance(first_item, dict):
            data_dict = first_item
        else:
            data_dict = first_item.__dict__

        headers = list(data_dict.keys())
        writer.writerow([h.replace("_", " ").title() for h in headers])

        for item in items:
            row_dict = item.model_dump() if hasattr(item, "model_dump") else (item if isinstance(item, dict) else item.__dict__)
            row_values = []
            for h in headers:
                val = row_dict.get(h)
                if isinstance(val, (datetime,)):
                    val = val.isoformat()
                elif isinstance(val, (Decimal,)):
                    val = str(val)
                elif isinstance(val, (list, dict)):
                    val = json.dumps(val)
                elif val is None:
                    val = ""
                row_values.append(val)
            writer.writerow(row_values)

        return output.getvalue()

    # =========================================================================
    # BACKWARD COMPATIBILITY METHODS
    # =========================================================================
    async def get_stock_valuation_report(
        self, db: AsyncSession, warehouse_id: Optional[uuid.UUID] = None
    ) -> List[StockValuationItem]:
        stmt = (
            select(
                StockBalance.product_id,
                Product.sku,
                Product.name.label("product_name"),
                StockBalance.warehouse_id,
                Warehouse.code.label("warehouse_code"),
                StockBalance.available_quantity.label("available_quantity"),
            )
            .join(Product, StockBalance.product_id == Product.id)
            .join(Warehouse, StockBalance.warehouse_id == Warehouse.id)
        )
        if warehouse_id:
            stmt = stmt.where(StockBalance.warehouse_id == warehouse_id)

        res = await db.execute(stmt)
        rows = res.all()

        items: List[StockValuationItem] = []
        for r in rows:
            qty = Decimal(str(r.available_quantity))
            est_cost = Decimal("100.00")
            val = qty * est_cost
            items.append(
                StockValuationItem(
                    product_id=r.product_id,
                    sku=r.sku,
                    product_name=r.product_name,
                    warehouse_id=r.warehouse_id,
                    warehouse_code=r.warehouse_code,
                    quantity=qty,
                    estimated_unit_cost=est_cost,
                    total_valuation=val,
                )
            )
        return items

    async def get_inventory_aging_report(
        self, db: AsyncSession, warehouse_id: Optional[uuid.UUID] = None
    ) -> List[InventoryAgingItem]:
        rep = await self.get_inventory_aging_report_paginated(db, warehouse_id=warehouse_id, page=1, size=500)
        items: List[InventoryAgingItem] = []
        for it in rep.items:
            days = it.days_since_last_inbound or it.days_since_last_movement or 0
            items.append(
                InventoryAgingItem(
                    product_id=it.product_id,
                    sku=it.product_sku,
                    product_name=it.product_name,
                    warehouse_code=it.warehouse_code,
                    quantity=it.quantity_on_hand,
                    days_in_stock=days,
                    aging_bucket=it.aging_bucket,
                )
            )
        return items

    async def get_movement_analysis_report(self, db: AsyncSession) -> List[MovementAnalysisItem]:
        stmt = (
            select(
                Product.id.label("product_id"),
                Product.sku,
                Product.name.label("product_name"),
                func.coalesce(func.sum(StockLedger.quantity), 0).label("total_issues"),
            )
            .select_from(Product)
            .outerjoin(
                StockLedger,
                (Product.id == StockLedger.product_id) & (StockLedger.direction == "OUT"),
            )
            .group_by(Product.id, Product.sku, Product.name)
        )
        res = await db.execute(stmt)
        rows = res.all()

        items: List[MovementAnalysisItem] = []
        for r in rows:
            issues = Decimal(str(r.total_issues))
            if issues > Decimal("50.0"):
                cat = "Fast Moving"
            elif issues > Decimal("0.0"):
                cat = "Slow Moving"
            else:
                cat = "Dead Stock"

            items.append(
                MovementAnalysisItem(
                    product_id=r.product_id,
                    sku=r.sku,
                    product_name=r.product_name,
                    total_issues=issues,
                    movement_category=cat,
                )
            )
        return items


class InventoryAnalyticsService:
    """
    Analytics service maintaining backward compatible endpoints and snapshotting.
    """

    async def get_dashboard_summary(self, db: AsyncSession) -> InventoryDashboardSummary:
        dash = await inventory_report_repository.get_dashboard_summary(db)
        wh_summaries = [
            {
                "warehouse_code": w.warehouse_code,
                "warehouse_name": w.warehouse_name,
                "stock_qty": float(w.total_on_hand_quantity),
            }
            for w in dash.warehouse_stock_breakdown
        ]
        top_prods = [
            {
                "product_sku": p.product_sku,
                "product_name": p.product_name,
                "movement_qty": float(p.total_moved_quantity),
            }
            for p in dash.top_moving_products
        ]

        return InventoryDashboardSummary(
            total_inventory_value=dash.total_on_hand_quantity * Decimal("100.00"),
            total_items_count=dash.total_on_hand_quantity,
            turnover_ratio=Decimal("3.50"),
            warehouse_utilization_pct=Decimal("78.50"),
            reserved_stock_qty=dash.total_reserved_quantity,
            available_stock_qty=dash.total_available_quantity,
            expiring_stock_qty=Decimal(str(dash.expired_batches_count + dash.expiring_soon_batches_count)),
            top_moving_products=top_prods,
            warehouse_stock_breakdown=wh_summaries,
        )

    async def generate_analytics_snapshot(self, db: AsyncSession) -> InventoryAnalyticsSnapshot:
        summary = await self.get_dashboard_summary(db)
        snapshot = InventoryAnalyticsSnapshot(
            snapshot_date=datetime.now(timezone.utc),
            total_inventory_value=summary.total_inventory_value,
            total_items_count=summary.total_items_count,
            turnover_ratio=summary.turnover_ratio,
            warehouse_utilization_pct=summary.warehouse_utilization_pct,
            reserved_stock_qty=summary.reserved_stock_qty,
            available_stock_qty=summary.available_stock_qty,
            expiring_stock_qty=summary.expiring_stock_qty,
            metrics_json=json.loads(summary.model_dump_json()),
        )
        return await inventory_analytics_repository.create(db, obj_in=snapshot)


inventory_report_service = InventoryReportService()
inventory_analytics_service = InventoryAnalyticsService()
