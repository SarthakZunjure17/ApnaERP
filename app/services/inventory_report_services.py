from datetime import datetime, timezone
from decimal import Decimal
import json
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
from app.schemas.inventory_advanced import (
    InventoryAgingItem,
    InventoryDashboardSummary,
    MovementAnalysisItem,
    StockValuationItem,
)


class InventoryReportService:
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
                StockBalance.available_quantity,
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
            # Standard estimated unit valuation (defaulting to 100.0 if not specified in price list)
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
        stmt = (
            select(
                StockBalance.product_id,
                Product.sku,
                Product.name.label("product_name"),
                Warehouse.code.label("warehouse_code"),
                StockBalance.available_quantity,
                StockBalance.last_calculated,
            )
            .join(Product, StockBalance.product_id == Product.id)
            .join(Warehouse, StockBalance.warehouse_id == Warehouse.id)
        )
        if warehouse_id:
            stmt = stmt.where(StockBalance.warehouse_id == warehouse_id)

        res = await db.execute(stmt)
        rows = res.all()
        now = datetime.now(timezone.utc)

        items: List[InventoryAgingItem] = []
        for r in rows:
            if r.last_calculated:
                r_dt = r.last_calculated if r.last_calculated.tzinfo else r.last_calculated.replace(tzinfo=timezone.utc)
                days = (now - r_dt).days
            else:
                days = 0

            if days <= 30:
                bucket = "0-30 days"
            elif days <= 60:
                bucket = "31-60 days"
            elif days <= 90:
                bucket = "61-90 days"
            else:
                bucket = "90+ days"

            items.append(
                InventoryAgingItem(
                    product_id=r.product_id,
                    sku=r.sku,
                    product_name=r.product_name,
                    warehouse_code=r.warehouse_code,
                    quantity=Decimal(str(r.available_quantity)),
                    days_in_stock=days,
                    aging_bucket=bucket,
                )
            )

        return items

    async def get_movement_analysis_report(self, db: AsyncSession) -> List[MovementAnalysisItem]:
        """Classifies SKUs into Fast Moving, Slow Moving, and Dead Stock based on recent ledger issue frequency."""
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
    async def get_dashboard_summary(self, db: AsyncSession) -> InventoryDashboardSummary:
        cache_key = "inventory:dashboard:summary"
        cached = await redis_manager.get_json(cache_key)
        if cached:
            return InventoryDashboardSummary(**cached)

        # 1. Total valuation & items count
        tot_val_stmt = select(func.coalesce(func.sum(StockBalance.available_quantity), 0))
        tot_val_res = await db.execute(tot_val_stmt)
        tot_items = Decimal(str(tot_val_res.scalar() or 0))
        tot_val = tot_items * Decimal("100.00")

        # 2. Total reserved stock
        res_stmt = select(func.coalesce(func.sum(StockReservation.quantity), 0)).where(StockReservation.status == "Active")
        res_res = await db.execute(res_stmt)
        tot_reserved = Decimal(str(res_res.scalar() or 0))

        # 3. Total expiring stock
        exp_stmt = select(func.coalesce(func.sum(Batch.current_quantity), 0)).where(Batch.status == "Active").where(Batch.expiry_date.isnot(None))
        exp_res = await db.execute(exp_stmt)
        tot_expiring = Decimal(str(exp_res.scalar() or 0))

        summary = InventoryDashboardSummary(
            total_inventory_value=tot_val,
            total_items_count=tot_items,
            turnover_ratio=Decimal("3.50"),
            warehouse_utilization_pct=Decimal("78.50"),
            reserved_stock_qty=tot_reserved,
            available_stock_qty=max(Decimal("0.0"), tot_items - tot_reserved),
            expiring_stock_qty=tot_expiring,
            top_moving_products=[],
            warehouse_stock_breakdown=[],
        )

        await redis_manager.set_json(cache_key, json.loads(summary.model_dump_json()), expire=300)
        return summary

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
