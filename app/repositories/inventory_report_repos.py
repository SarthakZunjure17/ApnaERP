from datetime import datetime, timezone, timedelta
from decimal import Decimal
import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, case, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.batch import Batch
from app.models.product import Product
from app.models.product_category import ProductCategory
from app.models.product_warehouse import ProductWarehouse
from app.models.serial_number import SerialNumber
from app.models.stock_balance import StockBalance
from app.models.stock_ledger import StockLedger
from app.models.stock_reservation import StockReservation
from app.models.storage_location import StorageLocation
from app.models.unit_of_measure import UnitOfMeasure
from app.models.warehouse import Warehouse
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
    MovementAnalyticsCategoryBreakdown,
    MovementAnalyticsTimelineBucket,
    MovementAnalyticsTypeBreakdown,
    MovementAnalyticsWarehouseBreakdown,
    ProductInventoryReportItem,
    SerialInventoryReportItem,
    StockMovementReportItem,
    StockMovementReportSummary,
    StockReportItem,
    StockReportSummary,
    StockReservationReportItem,
    StockReservationReportSummary,
    TopMovingProductItem,
    WarehouseInventoryReportItem,
    WarehouseUtilizationSummary,
)


class InventoryReportRepository:
    """
    High-performance read-only repository executing database-side aggregations,
    filtering, joins, and pagination across authoritative inventory data.
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
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[StockReportItem], int, StockReportSummary]:
        stmt = (
            select(
                StockBalance.product_id,
                Product.sku.label("product_sku"),
                Product.name.label("product_name"),
                Product.category_id,
                ProductCategory.name.label("category_name"),
                UnitOfMeasure.symbol.label("uom_symbol"),
                func.coalesce(Product.tracking_type, "NONE").label("tracking_type"),
                StockBalance.warehouse_id,
                Warehouse.code.label("warehouse_code"),
                Warehouse.name.label("warehouse_name"),
                StockBalance.storage_location_id,
                StorageLocation.code.label("storage_location_code"),
                StorageLocation.name.label("storage_location_name"),
                StockBalance.available_quantity.label("quantity_on_hand"),
                StockBalance.reserved_quantity,
                (StockBalance.available_quantity - StockBalance.reserved_quantity).label("available_quantity"),
                StockBalance.damaged_quantity,
                StockBalance.in_transit_quantity,
                StockBalance.last_calculated.label("last_updated"),
            )
            .select_from(StockBalance)
            .join(Product, StockBalance.product_id == Product.id)
            .join(Warehouse, StockBalance.warehouse_id == Warehouse.id)
            .outerjoin(StorageLocation, StockBalance.storage_location_id == StorageLocation.id)
            .outerjoin(ProductCategory, Product.category_id == ProductCategory.id)
            .outerjoin(UnitOfMeasure, Product.base_unit_id == UnitOfMeasure.id)
        )

        filters = []
        if product_id:
            filters.append(StockBalance.product_id == product_id)
        if warehouse_id:
            filters.append(StockBalance.warehouse_id == warehouse_id)
        if storage_location_id:
            filters.append(StockBalance.storage_location_id == storage_location_id)
        if category_id:
            filters.append(Product.category_id == category_id)
        if tracking_type:
            filters.append(func.upper(Product.tracking_type) == tracking_type.upper())
        if active_only:
            filters.append(Product.status != "Archived")
            filters.append(Warehouse.is_active == True)

        if search:
            pattern = f"%{search}%"
            filters.append(
                or_(
                    Product.sku.ilike(pattern),
                    Product.name.ilike(pattern),
                    Warehouse.code.ilike(pattern),
                    Warehouse.name.ilike(pattern),
                )
            )

        if filters:
            stmt = stmt.where(and_(*filters))

        # Overall count and totals
        count_stmt = select(
            func.count(StockBalance.id),
            func.count(distinct(StockBalance.product_id)),
            func.coalesce(func.sum(StockBalance.available_quantity), 0),
            func.coalesce(func.sum(StockBalance.reserved_quantity), 0),
        )
        if filters:
            count_stmt = (
                count_stmt.select_from(StockBalance)
                .join(Product, StockBalance.product_id == Product.id)
                .join(Warehouse, StockBalance.warehouse_id == Warehouse.id)
                .outerjoin(ProductCategory, Product.category_id == ProductCategory.id)
                .where(and_(*filters))
            )
        else:
            count_stmt = count_stmt.select_from(StockBalance)

        count_res = (await db.execute(count_stmt)).one()
        total_records = count_res[0] or 0
        total_products = count_res[1] or 0
        tot_on_hand = Decimal(str(count_res[2] or 0))
        tot_reserved = Decimal(str(count_res[3] or 0))
        tot_available = tot_on_hand - tot_reserved

        summary = StockReportSummary(
            total_products_count=total_products,
            total_records_count=total_records,
            total_quantity_on_hand=tot_on_hand,
            total_reserved_quantity=tot_reserved,
            total_available_quantity=tot_available,
        )

        paginated_stmt = stmt.order_by(Product.sku.asc(), Warehouse.code.asc()).offset(skip).limit(limit)
        res = await db.execute(paginated_stmt)
        rows = res.all()

        items: List[StockReportItem] = []
        for r in rows:
            on_hand = Decimal(str(r.quantity_on_hand))
            reserved = Decimal(str(r.reserved_quantity))
            items.append(
                StockReportItem(
                    product_id=r.product_id,
                    product_sku=r.product_sku,
                    product_name=r.product_name,
                    category_id=r.category_id,
                    category_name=r.category_name,
                    uom_symbol=r.uom_symbol,
                    tracking_type=r.tracking_type,
                    warehouse_id=r.warehouse_id,
                    warehouse_code=r.warehouse_code,
                    warehouse_name=r.warehouse_name,
                    storage_location_id=r.storage_location_id,
                    storage_location_code=r.storage_location_code,
                    storage_location_name=r.storage_location_name,
                    quantity_on_hand=on_hand,
                    reserved_quantity=reserved,
                    available_quantity=on_hand - reserved,
                    damaged_quantity=Decimal(str(r.damaged_quantity or 0)),
                    in_transit_quantity=Decimal(str(r.in_transit_quantity or 0)),
                    last_updated=r.last_updated,
                )
            )

        return items, total_records, summary

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
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[StockMovementReportItem], int, StockMovementReportSummary]:
        stmt = (
            select(
                StockLedger.id.label("movement_id"),
                StockLedger.transaction_date,
                StockLedger.product_id,
                Product.sku.label("product_sku"),
                Product.name.label("product_name"),
                StockLedger.warehouse_id,
                Warehouse.code.label("warehouse_code"),
                StockLedger.storage_location_id,
                StorageLocation.code.label("storage_location_code"),
                StockLedger.movement_type,
                StockLedger.direction,
                StockLedger.quantity,
                StockLedger.quantity_before,
                StockLedger.quantity_after,
                StockLedger.running_balance,
                StockLedger.reference_type,
                StockLedger.reference_id,
                StockLedger.batch_id,
                Batch.batch_number,
                StockLedger.metadata_json,
                StockLedger.reason,
                StockLedger.notes,
                StockLedger.created_by,
            )
            .select_from(StockLedger)
            .join(Product, StockLedger.product_id == Product.id)
            .join(Warehouse, StockLedger.warehouse_id == Warehouse.id)
            .outerjoin(StorageLocation, StockLedger.storage_location_id == StorageLocation.id)
            .outerjoin(Batch, StockLedger.batch_id == Batch.id)
        )

        filters = []
        if product_id:
            filters.append(StockLedger.product_id == product_id)
        if warehouse_id:
            filters.append(StockLedger.warehouse_id == warehouse_id)
        if storage_location_id:
            filters.append(StockLedger.storage_location_id == storage_location_id)
        if movement_type:
            filters.append(func.upper(StockLedger.movement_type) == movement_type.upper())
        if direction:
            filters.append(func.upper(StockLedger.direction) == direction.upper())
        if batch_id:
            filters.append(StockLedger.batch_id == batch_id)
        if reference_type:
            filters.append(func.lower(StockLedger.reference_type) == reference_type.lower())
        if date_from:
            filters.append(StockLedger.transaction_date >= date_from)
        if date_to:
            filters.append(StockLedger.transaction_date <= date_to)

        if search:
            pattern = f"%{search}%"
            filters.append(
                or_(
                    Product.sku.ilike(pattern),
                    Product.name.ilike(pattern),
                    StockLedger.reason.ilike(pattern),
                    StockLedger.notes.ilike(pattern),
                )
            )

        if filters:
            stmt = stmt.where(and_(*filters))

        # Totals query
        sum_in = func.coalesce(
            func.sum(case((func.upper(StockLedger.direction) == "IN", StockLedger.quantity), else_=0)), 0
        )
        sum_out = func.coalesce(
            func.sum(case((func.upper(StockLedger.direction) == "OUT", StockLedger.quantity), else_=0)), 0
        )
        totals_stmt = select(func.count(StockLedger.id), sum_in, sum_out)
        if filters:
            totals_stmt = (
                totals_stmt.select_from(StockLedger)
                .join(Product, StockLedger.product_id == Product.id)
                .where(and_(*filters))
            )
        else:
            totals_stmt = totals_stmt.select_from(StockLedger)

        totals_res = (await db.execute(totals_stmt)).one()
        total_records = totals_res[0] or 0
        tot_in = Decimal(str(totals_res[1] or 0))
        tot_out = Decimal(str(totals_res[2] or 0))
        net_qty = tot_in - tot_out

        summary = StockMovementReportSummary(
            total_movements_count=total_records,
            total_inbound_quantity=tot_in,
            total_outbound_quantity=tot_out,
            net_movement_quantity=net_qty,
        )

        paginated_stmt = (
            stmt.order_by(StockLedger.transaction_date.desc(), StockLedger.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await db.execute(paginated_stmt)
        rows = res.all()

        items: List[StockMovementReportItem] = []
        for r in rows:
            items.append(
                StockMovementReportItem(
                    movement_id=r.movement_id,
                    transaction_date=r.transaction_date,
                    product_id=r.product_id,
                    product_sku=r.product_sku,
                    product_name=r.product_name,
                    warehouse_id=r.warehouse_id,
                    warehouse_code=r.warehouse_code,
                    storage_location_id=r.storage_location_id,
                    storage_location_code=r.storage_location_code,
                    movement_type=r.movement_type,
                    direction=r.direction,
                    quantity=Decimal(str(r.quantity)),
                    quantity_before=Decimal(str(r.quantity_before)),
                    quantity_after=Decimal(str(r.quantity_after)),
                    running_balance=Decimal(str(r.running_balance)),
                    reference_type=r.reference_type,
                    reference_id=r.reference_id,
                    batch_id=r.batch_id,
                    batch_number=r.batch_number,
                    serial_numbers=(
                        r.metadata_json.get("serial_numbers")
                        if r.metadata_json and isinstance(r.metadata_json, dict)
                        else None
                    ),
                    reason=r.reason,
                    notes=r.notes,
                    created_by=r.created_by,
                )
            )

        return items, total_records, summary

    # =========================================================================
    # 3. WAREHOUSE INVENTORY REPORT
    # =========================================================================
    async def get_warehouse_inventory_report(
        self,
        db: AsyncSession,
        warehouse_id: Optional[uuid.UUID] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[WarehouseInventoryReportItem], int]:
        wh_stmt = select(Warehouse)
        filters = []
        if warehouse_id:
            filters.append(Warehouse.id == warehouse_id)
        if is_active is not None:
            filters.append(Warehouse.is_active == is_active)
        if search:
            patt = f"%{search}%"
            filters.append(or_(Warehouse.code.ilike(patt), Warehouse.name.ilike(patt)))
        if filters:
            wh_stmt = wh_stmt.where(and_(*filters))

        count_stmt = select(func.count(Warehouse.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total = (await db.execute(count_stmt)).scalar() or 0

        paginated_whs = (await db.execute(wh_stmt.order_by(Warehouse.code.asc()).offset(skip).limit(limit))).scalars().all()

        items: List[WarehouseInventoryReportItem] = []
        now = datetime.now(timezone.utc)

        for wh in paginated_whs:
            # 1. Total storage locations
            loc_count = (
                await db.execute(
                    select(func.count(StorageLocation.id)).where(StorageLocation.warehouse_id == wh.id)
                )
            ).scalar() or 0

            # 2. Stock balances aggregation
            bal_stmt = select(
                func.count(distinct(StockBalance.product_id)),
                func.coalesce(func.sum(StockBalance.available_quantity), 0),
                func.coalesce(func.sum(StockBalance.reserved_quantity), 0),
            ).where(StockBalance.warehouse_id == wh.id)
            bal_res = (await db.execute(bal_stmt)).one()
            prod_count = bal_res[0] or 0
            on_hand = Decimal(str(bal_res[1] or 0))
            reserved = Decimal(str(bal_res[2] or 0))
            available = on_hand - reserved

            # 3. Tracked Batches
            batch_count = (
                await db.execute(
                    select(func.count(distinct(Batch.id)))
                    .select_from(StockBalance)
                    .join(Batch, StockBalance.product_id == Batch.product_id)
                    .where(StockBalance.warehouse_id == wh.id, Batch.status == "Active")
                )
            ).scalar() or 0

            # 4. Expired Batches
            expired_batch_count = (
                await db.execute(
                    select(func.count(distinct(Batch.id)))
                    .select_from(StockBalance)
                    .join(Batch, StockBalance.product_id == Batch.product_id)
                    .where(
                        StockBalance.warehouse_id == wh.id,
                        Batch.expiry_date.isnot(None),
                        Batch.expiry_date < now,
                    )
                )
            ).scalar() or 0

            # 5. Tracked Serials
            serial_count = (
                await db.execute(
                    select(func.count(SerialNumber.id)).where(
                        SerialNumber.warehouse_id == wh.id,
                        SerialNumber.status.in_(["Available", "Reserved"]),
                    )
                )
            ).scalar() or 0

            # 6. Low stock items
            low_stock_count = (
                await db.execute(
                    select(func.count(distinct(StockBalance.product_id)))
                    .select_from(StockBalance)
                    .join(Product, StockBalance.product_id == Product.id)
                    .where(
                        StockBalance.warehouse_id == wh.id,
                        Product.reorder_level > 0,
                        StockBalance.available_quantity <= Product.reorder_level,
                    )
                )
            ).scalar() or 0

            items.append(
                WarehouseInventoryReportItem(
                    warehouse_id=wh.id,
                    warehouse_code=wh.code,
                    warehouse_name=wh.name,
                    is_active=wh.is_active,
                    total_products_stocked=prod_count,
                    total_storage_locations=loc_count,
                    total_on_hand_quantity=on_hand,
                    total_reserved_quantity=reserved,
                    total_available_quantity=available,
                    active_tracked_batches_count=batch_count,
                    tracked_serials_count=serial_count,
                    expired_batches_count=expired_batch_count,
                    low_stock_items_count=low_stock_count,
                )
            )

        return items, total

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
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[ProductInventoryReportItem], int]:
        prod_stmt = (
            select(
                Product,
                ProductCategory.name.label("category_name"),
                UnitOfMeasure.symbol.label("uom_symbol"),
            )
            .select_from(Product)
            .outerjoin(ProductCategory, Product.category_id == ProductCategory.id)
            .outerjoin(UnitOfMeasure, Product.base_unit_id == UnitOfMeasure.id)
        )

        filters = []
        if product_id:
            filters.append(Product.id == product_id)
        if category_id:
            filters.append(Product.category_id == category_id)
        if tracking_type:
            filters.append(func.upper(Product.tracking_type) == tracking_type.upper())
        if search:
            patt = f"%{search}%"
            filters.append(or_(Product.sku.ilike(patt), Product.name.ilike(patt)))

        if filters:
            prod_stmt = prod_stmt.where(and_(*filters))

        count_stmt = select(func.count(Product.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total = (await db.execute(count_stmt)).scalar() or 0

        paginated_res = await db.execute(prod_stmt.order_by(Product.sku.asc()).offset(skip).limit(limit))
        rows = paginated_res.all()

        items: List[ProductInventoryReportItem] = []
        for r in rows:
            prod = r[0]
            cat_name = r.category_name
            uom_sym = r.uom_symbol

            # Balances
            bal_stmt = select(
                func.coalesce(func.sum(StockBalance.available_quantity), 0),
                func.coalesce(func.sum(StockBalance.reserved_quantity), 0),
                func.count(distinct(StockBalance.warehouse_id)),
                func.count(distinct(StockBalance.storage_location_id)),
            ).where(StockBalance.product_id == prod.id)
            bal_res = (await db.execute(bal_stmt)).one()
            on_hand = Decimal(str(bal_res[0] or 0))
            reserved = Decimal(str(bal_res[1] or 0))
            available = on_hand - reserved
            wh_count = bal_res[2] or 0
            loc_count = bal_res[3] or 0

            # Batches and Serials
            batch_count = (
                await db.execute(select(func.count(Batch.id)).where(Batch.product_id == prod.id))
            ).scalar() or 0
            serial_count = (
                await db.execute(select(func.count(SerialNumber.id)).where(SerialNumber.product_id == prod.id))
            ).scalar() or 0

            # Recent Movements
            last_mov_stmt = (
                select(StockLedger.transaction_date, StockLedger.quantity)
                .where(StockLedger.product_id == prod.id)
                .order_by(StockLedger.transaction_date.desc(), StockLedger.created_at.desc())
                .limit(1)
            )
            last_mov = (await db.execute(last_mov_stmt)).first()
            last_date = last_mov[0] if last_mov else None
            recent_qty = Decimal(str(last_mov[1])) if last_mov else Decimal("0.0")

            items.append(
                ProductInventoryReportItem(
                    product_id=prod.id,
                    product_sku=prod.sku,
                    product_name=prod.name,
                    category_id=prod.category_id,
                    category_name=cat_name,
                    uom_symbol=uom_sym,
                    tracking_type=prod.tracking_type or "NONE",
                    is_active=prod.is_active,
                    status=prod.status,
                    total_on_hand=on_hand,
                    total_reserved=reserved,
                    total_available=available,
                    warehouses_count=wh_count,
                    locations_count=loc_count,
                    batches_count=batch_count,
                    serials_count=serial_count,
                    recent_movement_quantity=recent_qty,
                    last_movement_date=last_date,
                )
            )

        return items, total

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
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[BatchExpiryReportItem], int, BatchExpiryReportSummary]:
        stmt = (
            select(Batch, Product.sku.label("product_sku"), Product.name.label("product_name"))
            .select_from(Batch)
            .join(Product, Batch.product_id == Product.id)
        )

        now = datetime.now(timezone.utc)
        filters = []
        if product_id:
            filters.append(Batch.product_id == product_id)
        if status:
            filters.append(func.upper(Batch.status) == status.upper())
        if date_from:
            filters.append(Batch.expiry_date >= date_from)
        if date_to:
            filters.append(Batch.expiry_date <= date_to)

        if expiring_within_days is not None:
            horizon = now + timedelta(days=expiring_within_days)
            filters.append(Batch.expiry_date.isnot(None))
            filters.append(Batch.expiry_date >= now)
            filters.append(Batch.expiry_date <= horizon)

        if expiry_status:
            exp_s = expiry_status.lower()
            if exp_s == "expired":
                filters.append(Batch.expiry_date.isnot(None))
                filters.append(Batch.expiry_date < now)
            elif exp_s in ["expiring_soon", "expiring soon"]:
                horizon = now + timedelta(days=30)
                filters.append(Batch.expiry_date.isnot(None))
                filters.append(Batch.expiry_date >= now)
                filters.append(Batch.expiry_date <= horizon)
            elif exp_s in ["not_expiring", "no_expiry"]:
                filters.append(Batch.expiry_date.is_(None))
            elif exp_s == "normal":
                horizon = now + timedelta(days=30)
                filters.append(Batch.expiry_date.isnot(None))
                filters.append(Batch.expiry_date > horizon)

        if search:
            patt = f"%{search}%"
            filters.append(
                or_(
                    Batch.batch_number.ilike(patt),
                    Product.sku.ilike(patt),
                    Product.name.ilike(patt),
                )
            )

        if filters:
            stmt = stmt.where(and_(*filters))

        count_stmt = select(
            func.count(Batch.id),
            func.coalesce(func.sum(Batch.current_quantity), 0),
            func.coalesce(
                func.sum(
                    case((and_(Batch.expiry_date.isnot(None), Batch.expiry_date < now), Batch.current_quantity), else_=0)
                ),
                0,
            ),
        )
        if filters:
            count_stmt = (
                count_stmt.select_from(Batch)
                .join(Product, Batch.product_id == Product.id)
                .where(and_(*filters))
            )
        else:
            count_stmt = count_stmt.select_from(Batch)

        count_res = (await db.execute(count_stmt)).one()
        total_batches = count_res[0] or 0
        total_stock_qty = Decimal(str(count_res[1] or 0))
        expired_stock_qty = Decimal(str(count_res[2] or 0))

        # Additional summary metrics
        active_count = (await db.execute(select(func.count(Batch.id)).where(Batch.status == "Active"))).scalar() or 0
        expired_count = (
            await db.execute(
                select(func.count(Batch.id)).where(
                    Batch.expiry_date.isnot(None),
                    Batch.expiry_date < now,
                )
            )
        ).scalar() or 0
        expiring_soon_count = (
            await db.execute(
                select(func.count(Batch.id)).where(
                    Batch.expiry_date.isnot(None),
                    Batch.expiry_date >= now,
                    Batch.expiry_date <= now + timedelta(days=30),
                )
            )
        ).scalar() or 0

        summary = BatchExpiryReportSummary(
            total_batches_count=total_batches,
            active_batches_count=active_count,
            expired_batches_count=expired_count,
            expiring_soon_batches_count=expiring_soon_count,
            total_batch_stock_quantity=total_stock_qty,
            expired_stock_quantity=expired_stock_qty,
        )

        paginated_stmt = stmt.order_by(Batch.expiry_date.asc().nulls_last()).offset(skip).limit(limit)
        res = await db.execute(paginated_stmt)
        rows = res.all()

        items: List[BatchExpiryReportItem] = []
        for r in rows:
            b: Batch = r[0]
            sku = r.product_sku
            name = r.product_name

            days_left = None
            exp_status = "No Expiry"
            if b.expiry_date:
                b_exp = b.expiry_date if b.expiry_date.tzinfo else b.expiry_date.replace(tzinfo=timezone.utc)
                delta = b_exp - now
                days_left = delta.days
                if delta.total_seconds() < 0:
                    exp_status = "Expired"
                elif days_left <= 30:
                    exp_status = "Expiring Soon"
                else:
                    exp_status = "Normal"

            items.append(
                BatchExpiryReportItem(
                    batch_id=b.id,
                    batch_number=b.batch_number,
                    product_id=b.product_id,
                    product_sku=sku,
                    product_name=name,
                    manufacturing_date=b.manufacturing_date,
                    expiry_date=b.expiry_date,
                    days_until_expiry=days_left,
                    supplier_batch_ref=b.supplier_batch_ref,
                    current_quantity=Decimal(str(b.current_quantity)),
                    status=b.status,
                    expiry_status=exp_status,
                    notes=b.notes,
                )
            )

        return items, total_batches, summary

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
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[SerialInventoryReportItem], int]:
        stmt = (
            select(
                SerialNumber,
                Product.sku.label("product_sku"),
                Product.name.label("product_name"),
                Warehouse.code.label("warehouse_code"),
                StorageLocation.code.label("storage_location_code"),
                Batch.batch_number,
            )
            .select_from(SerialNumber)
            .join(Product, SerialNumber.product_id == Product.id)
            .outerjoin(Warehouse, SerialNumber.warehouse_id == Warehouse.id)
            .outerjoin(StorageLocation, SerialNumber.storage_location_id == StorageLocation.id)
            .outerjoin(Batch, SerialNumber.batch_id == Batch.id)
        )

        filters = []
        if product_id:
            filters.append(SerialNumber.product_id == product_id)
        if warehouse_id:
            filters.append(SerialNumber.warehouse_id == warehouse_id)
        if storage_location_id:
            filters.append(SerialNumber.storage_location_id == storage_location_id)
        if batch_id:
            filters.append(SerialNumber.batch_id == batch_id)
        if status:
            filters.append(func.upper(SerialNumber.status) == status.upper())
        if search:
            patt = f"%{search}%"
            filters.append(
                or_(
                    SerialNumber.serial_number.ilike(patt),
                    Product.sku.ilike(patt),
                    Product.name.ilike(patt),
                )
            )

        if filters:
            stmt = stmt.where(and_(*filters))

        count_stmt = select(func.count(SerialNumber.id))
        if filters:
            count_stmt = count_stmt.select_from(SerialNumber).join(Product, SerialNumber.product_id == Product.id).where(and_(*filters))
        else:
            count_stmt = count_stmt.select_from(SerialNumber)

        total = (await db.execute(count_stmt)).scalar() or 0
        paginated_res = await db.execute(stmt.order_by(SerialNumber.serial_number.asc()).offset(skip).limit(limit))
        rows = paginated_res.all()

        items: List[SerialInventoryReportItem] = []
        for r in rows:
            s: SerialNumber = r[0]
            sku = r.product_sku
            pname = r.product_name
            wh_code = r.warehouse_code
            loc_code = r.storage_location_code
            b_num = r.batch_number

            hist = list(s.history or [])
            last_ev = hist[-1] if hist else None

            items.append(
                SerialInventoryReportItem(
                    serial_id=s.id,
                    serial_number=s.serial_number,
                    product_id=s.product_id,
                    product_sku=sku,
                    product_name=pname,
                    batch_id=s.batch_id,
                    batch_number=b_num,
                    warehouse_id=s.warehouse_id,
                    warehouse_code=wh_code,
                    storage_location_id=s.storage_location_id,
                    storage_location_code=loc_code,
                    status=s.status,
                    history_events_count=len(hist),
                    last_event=last_ev,
                    created_at=s.created_at,
                    updated_at=s.updated_at,
                )
            )

        return items, total

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
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[StockReservationReportItem], int, StockReservationReportSummary]:
        stmt = (
            select(
                StockReservation,
                Product.sku.label("product_sku"),
                Product.name.label("product_name"),
                Warehouse.code.label("warehouse_code"),
                StorageLocation.code.label("storage_location_code"),
                Batch.batch_number,
            )
            .select_from(StockReservation)
            .join(Product, StockReservation.product_id == Product.id)
            .join(Warehouse, StockReservation.warehouse_id == Warehouse.id)
            .outerjoin(StorageLocation, StockReservation.storage_location_id == StorageLocation.id)
            .outerjoin(Batch, StockReservation.batch_id == Batch.id)
        )

        filters = []
        if product_id:
            filters.append(StockReservation.product_id == product_id)
        if warehouse_id:
            filters.append(StockReservation.warehouse_id == warehouse_id)
        if status:
            filters.append(func.upper(StockReservation.status) == status.upper())
        if reserved_for_type:
            filters.append(func.upper(StockReservation.reserved_for_type) == reserved_for_type.upper())
        if date_from:
            filters.append(StockReservation.created_at >= date_from)
        if date_to:
            filters.append(StockReservation.created_at <= date_to)

        if search:
            patt = f"%{search}%"
            filters.append(
                or_(
                    StockReservation.reservation_number.ilike(patt),
                    Product.sku.ilike(patt),
                    Product.name.ilike(patt),
                )
            )

        if filters:
            stmt = stmt.where(and_(*filters))

        count_stmt = select(
            func.count(StockReservation.id),
            func.coalesce(
                func.sum(case((func.upper(StockReservation.status) == "ACTIVE", StockReservation.quantity), else_=0)), 0
            ),
        )
        if filters:
            count_stmt = count_stmt.select_from(StockReservation).join(Product, StockReservation.product_id == Product.id).where(and_(*filters))
        else:
            count_stmt = count_stmt.select_from(StockReservation)

        count_res = (await db.execute(count_stmt)).one()
        total_res = count_res[0] or 0
        tot_active_qty = Decimal(str(count_res[1] or 0))

        active_cnt = (await db.execute(select(func.count(StockReservation.id)).where(StockReservation.status == "Active"))).scalar() or 0
        released_cnt = (await db.execute(select(func.count(StockReservation.id)).where(StockReservation.status == "Released"))).scalar() or 0
        consumed_cnt = (await db.execute(select(func.count(StockReservation.id)).where(StockReservation.status == "Consumed"))).scalar() or 0

        summary = StockReservationReportSummary(
            total_reservations_count=total_res,
            active_reservations_count=active_cnt,
            released_reservations_count=released_cnt,
            consumed_reservations_count=consumed_cnt,
            total_active_reserved_quantity=tot_active_qty,
        )

        paginated_res = await db.execute(
            stmt.order_by(StockReservation.created_at.desc()).offset(skip).limit(limit)
        )
        rows = paginated_res.all()

        items: List[StockReservationReportItem] = []
        for r in rows:
            res_obj: StockReservation = r[0]
            items.append(
                StockReservationReportItem(
                    reservation_id=res_obj.id,
                    reservation_number=res_obj.reservation_number,
                    product_id=res_obj.product_id,
                    product_sku=r.product_sku,
                    product_name=r.product_name,
                    warehouse_id=res_obj.warehouse_id,
                    warehouse_code=r.warehouse_code,
                    storage_location_id=res_obj.storage_location_id,
                    storage_location_code=r.storage_location_code,
                    batch_id=res_obj.batch_id,
                    batch_number=r.batch_number,
                    quantity=Decimal(str(res_obj.quantity)),
                    reserved_for_type=res_obj.reserved_for_type,
                    reference_type=res_obj.reserved_for_type,
                    reserved_for_id=res_obj.reserved_for_id,
                    reference_id=res_obj.reserved_for_id,
                    status=res_obj.status,
                    expires_at=res_obj.expires_at,
                    released_at=res_obj.released_at,
                    consumed_at=res_obj.consumed_at,
                    remarks=res_obj.remarks,
                    notes=res_obj.remarks,
                    created_by=res_obj.created_by,
                    created_at=res_obj.created_at,
                )
            )

        return items, total_res, summary

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
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[AvailableStockReportItem], int]:
        stmt = (
            select(
                StockBalance.product_id,
                Product.sku.label("product_sku"),
                Product.name.label("product_name"),
                func.coalesce(Product.tracking_type, "NONE").label("tracking_type"),
                StockBalance.warehouse_id,
                Warehouse.code.label("warehouse_code"),
                StockBalance.storage_location_id,
                StorageLocation.code.label("storage_location_code"),
                StockBalance.available_quantity.label("quantity_on_hand"),
                StockBalance.reserved_quantity,
            )
            .select_from(StockBalance)
            .join(Product, StockBalance.product_id == Product.id)
            .join(Warehouse, StockBalance.warehouse_id == Warehouse.id)
            .outerjoin(StorageLocation, StockBalance.storage_location_id == StorageLocation.id)
        )

        filters = []
        if product_id:
            filters.append(StockBalance.product_id == product_id)
        if warehouse_id:
            filters.append(StockBalance.warehouse_id == warehouse_id)
        if storage_location_id:
            filters.append(StockBalance.storage_location_id == storage_location_id)
        if category_id:
            filters.append(Product.category_id == category_id)
        if tracking_type:
            filters.append(func.upper(Product.tracking_type) == tracking_type.upper())
        if search:
            patt = f"%{search}%"
            filters.append(
                or_(
                    Product.sku.ilike(patt),
                    Product.name.ilike(patt),
                    Warehouse.code.ilike(patt),
                )
            )

        if filters:
            stmt = stmt.where(and_(*filters))

        count_stmt = select(func.count(StockBalance.id))
        if filters:
            count_stmt = count_stmt.select_from(StockBalance).join(Product, StockBalance.product_id == Product.id).where(and_(*filters))
        else:
            count_stmt = count_stmt.select_from(StockBalance)

        total = (await db.execute(count_stmt)).scalar() or 0
        paginated_res = await db.execute(
            stmt.order_by(Product.sku.asc(), Warehouse.code.asc()).offset(skip).limit(limit)
        )
        rows = paginated_res.all()

        items: List[AvailableStockReportItem] = []
        for r in rows:
            on_hand = Decimal(str(r.quantity_on_hand))
            reserved = Decimal(str(r.reserved_quantity))
            avail = max(Decimal("0.0"), on_hand - reserved)

            items.append(
                AvailableStockReportItem(
                    product_id=r.product_id,
                    product_sku=r.product_sku,
                    product_name=r.product_name,
                    tracking_type=r.tracking_type,
                    warehouse_id=r.warehouse_id,
                    warehouse_code=r.warehouse_code,
                    storage_location_id=r.storage_location_id,
                    storage_location_code=r.storage_location_code,
                    on_hand_quantity=on_hand,
                    reserved_quantity=reserved,
                    available_quantity=avail,
                )
            )

        return items, total

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
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[LowStockReportItem], int, LowStockReportSummary]:
        # Query total stock per product (and optionally warehouse) and compare with reorder thresholds
        stmt = (
            select(
                Product.id.label("product_id"),
                Product.sku.label("product_sku"),
                Product.name.label("product_name"),
                Product.category_id,
                ProductCategory.name.label("category_name"),
                func.coalesce(Product.reorder_level, 0).label("reorder_level"),
                func.coalesce(Product.reorder_quantity, 0).label("reorder_quantity"),
                func.coalesce(Product.minimum_stock, 0).label("minimum_stock"),
                func.coalesce(Product.maximum_stock, 0).label("maximum_stock"),
                func.coalesce(func.sum(StockBalance.available_quantity), 0).label("total_on_hand"),
            )
            .select_from(Product)
            .outerjoin(StockBalance, Product.id == StockBalance.product_id)
            .outerjoin(ProductCategory, Product.category_id == ProductCategory.id)
            .group_by(
                Product.id,
                Product.sku,
                Product.name,
                Product.category_id,
                ProductCategory.name,
                Product.reorder_level,
                Product.reorder_quantity,
                Product.minimum_stock,
                Product.maximum_stock,
            )
        )

        filters = []
        if warehouse_id:
            filters.append(StockBalance.warehouse_id == warehouse_id)
        if category_id:
            filters.append(Product.category_id == category_id)
        if search:
            patt = f"%{search}%"
            filters.append(or_(Product.sku.ilike(patt), Product.name.ilike(patt)))

        if filters:
            stmt = stmt.where(and_(*filters))

        res = await db.execute(stmt.order_by(Product.sku.asc()))
        all_rows = res.all()

        low_stock_items: List[LowStockReportItem] = []
        tot_shortage = Decimal("0.0")
        below_reorder_cnt = 0
        below_min_cnt = 0

        for r in all_rows:
            on_hand = Decimal(str(r.total_on_hand))
            reorder_lvl = Decimal(str(r.reorder_level))
            reorder_qty = Decimal(str(r.reorder_quantity))
            min_stock = Decimal(str(r.minimum_stock))
            max_stock = Decimal(str(r.maximum_stock)) if r.maximum_stock else None

            is_below_reorder = (reorder_lvl > Decimal("0.0")) and (on_hand < reorder_lvl)
            is_below_min = (min_stock > Decimal("0.0")) and (on_hand < min_stock)

            if below_reorder_only and not is_below_reorder:
                continue
            if below_min_only and not is_below_min:
                continue

            shortage = max(Decimal("0.0"), (reorder_lvl if reorder_lvl > 0 else min_stock) - on_hand)
            if is_below_reorder:
                below_reorder_cnt += 1
            if is_below_min:
                below_min_cnt += 1
            tot_shortage += shortage

            low_stock_items.append(
                LowStockReportItem(
                    product_id=r.product_id,
                    product_sku=r.product_sku,
                    product_name=r.product_name,
                    category_id=r.category_id,
                    category_name=r.category_name,
                    warehouse_id=warehouse_id,
                    warehouse_code=None,
                    on_hand_quantity=on_hand,
                    reorder_level=reorder_lvl,
                    reorder_quantity=reorder_qty,
                    minimum_stock=min_stock,
                    maximum_stock=max_stock,
                    below_reorder_level=is_below_reorder,
                    below_minimum_stock=is_below_min,
                    shortage_quantity=shortage,
                )
            )

        total_items = len(low_stock_items)
        paginated_items = low_stock_items[skip : skip + limit]

        summary = LowStockReportSummary(
            total_low_stock_items=below_reorder_cnt,
            total_below_min_items=below_min_cnt,
            total_shortage_quantity=tot_shortage,
        )

        return paginated_items, total_items, summary

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
        base_stmt = select(StockLedger).select_from(StockLedger).join(Product, StockLedger.product_id == Product.id)

        filters = []
        if date_from:
            filters.append(StockLedger.transaction_date >= date_from)
        if date_to:
            filters.append(StockLedger.transaction_date <= date_to)
        if product_id:
            filters.append(StockLedger.product_id == product_id)
        if warehouse_id:
            filters.append(StockLedger.warehouse_id == warehouse_id)
        if category_id:
            filters.append(Product.category_id == category_id)

        # 1. Overall Totals
        sum_in = func.coalesce(
            func.sum(case((func.upper(StockLedger.direction) == "IN", StockLedger.quantity), else_=0)), 0
        )
        sum_out = func.coalesce(
            func.sum(case((func.upper(StockLedger.direction) == "OUT", StockLedger.quantity), else_=0)), 0
        )
        tot_stmt = select(func.count(StockLedger.id), sum_in, sum_out)
        if filters:
            tot_stmt = tot_stmt.select_from(StockLedger).join(Product, StockLedger.product_id == Product.id).where(and_(*filters))
        else:
            tot_stmt = tot_stmt.select_from(StockLedger)

        tot_res = (await db.execute(tot_stmt)).one()
        total_movements = tot_res[0] or 0
        total_in = Decimal(str(tot_res[1] or 0))
        total_out = Decimal(str(tot_res[2] or 0))

        # 2. Movement Type Breakdown
        type_stmt = (
            select(
                StockLedger.movement_type,
                StockLedger.direction,
                func.coalesce(func.sum(StockLedger.quantity), 0),
                func.count(StockLedger.id),
            )
            .select_from(StockLedger)
            .join(Product, StockLedger.product_id == Product.id)
            .group_by(StockLedger.movement_type, StockLedger.direction)
        )
        if filters:
            type_stmt = type_stmt.where(and_(*filters))
        type_res = (await db.execute(type_stmt)).all()
        type_breakdown = [
            MovementAnalyticsTypeBreakdown(
                movement_type=r[0],
                direction=r[1],
                total_quantity=Decimal(str(r[2])),
                movement_count=r[3],
            )
            for r in type_res
        ]

        # 3. Category Breakdown
        cat_stmt = (
            select(
                Product.category_id,
                func.coalesce(ProductCategory.name, "Uncategorized"),
                func.coalesce(
                    func.sum(case((func.upper(StockLedger.direction) == "IN", StockLedger.quantity), else_=0)), 0
                ),
                func.coalesce(
                    func.sum(case((func.upper(StockLedger.direction) == "OUT", StockLedger.quantity), else_=0)), 0
                ),
                func.count(StockLedger.id),
            )
            .select_from(StockLedger)
            .join(Product, StockLedger.product_id == Product.id)
            .outerjoin(ProductCategory, Product.category_id == ProductCategory.id)
            .group_by(Product.category_id, ProductCategory.name)
        )
        if filters:
            cat_stmt = cat_stmt.where(and_(*filters))
        cat_res = (await db.execute(cat_stmt)).all()
        cat_breakdown = [
            MovementAnalyticsCategoryBreakdown(
                category_id=r[0],
                category_name=r[1],
                inbound_quantity=Decimal(str(r[2])),
                outbound_quantity=Decimal(str(r[3])),
                movement_count=r[4],
            )
            for r in cat_res
        ]

        # 4. Warehouse Breakdown
        wh_stmt = (
            select(
                StockLedger.warehouse_id,
                Warehouse.code,
                Warehouse.name,
                func.coalesce(
                    func.sum(case((func.upper(StockLedger.direction) == "IN", StockLedger.quantity), else_=0)), 0
                ),
                func.coalesce(
                    func.sum(case((func.upper(StockLedger.direction) == "OUT", StockLedger.quantity), else_=0)), 0
                ),
                func.count(StockLedger.id),
            )
            .select_from(StockLedger)
            .join(Warehouse, StockLedger.warehouse_id == Warehouse.id)
            .join(Product, StockLedger.product_id == Product.id)
            .group_by(StockLedger.warehouse_id, Warehouse.code, Warehouse.name)
        )
        if filters:
            wh_stmt = wh_stmt.where(and_(*filters))
        wh_res = (await db.execute(wh_stmt)).all()
        wh_breakdown = [
            MovementAnalyticsWarehouseBreakdown(
                warehouse_id=r[0],
                warehouse_code=r[1],
                warehouse_name=r[2],
                inbound_quantity=Decimal(str(r[3])),
                outbound_quantity=Decimal(str(r[4])),
                movement_count=r[5],
            )
            for r in wh_res
        ]

        # 5. Timeline Breakdown (daily buckets)
        timeline_stmt = (
            select(
                func.date(StockLedger.transaction_date).label("period"),
                func.coalesce(
                    func.sum(case((func.upper(StockLedger.direction) == "IN", StockLedger.quantity), else_=0)), 0
                ),
                func.coalesce(
                    func.sum(case((func.upper(StockLedger.direction) == "OUT", StockLedger.quantity), else_=0)), 0
                ),
                func.count(StockLedger.id),
            )
            .select_from(StockLedger)
            .join(Product, StockLedger.product_id == Product.id)
            .group_by(func.date(StockLedger.transaction_date))
            .order_by(func.date(StockLedger.transaction_date).asc())
        )
        if filters:
            timeline_stmt = timeline_stmt.where(and_(*filters))
        timeline_res = (await db.execute(timeline_stmt)).all()
        timeline = [
            MovementAnalyticsTimelineBucket(
                period=str(r[0]),
                inbound_quantity=Decimal(str(r[1])),
                outbound_quantity=Decimal(str(r[2])),
                net_movement=Decimal(str(r[1])) - Decimal(str(r[2])),
                movement_count=r[3],
            )
            for r in timeline_res
        ]

        return InventoryMovementAnalyticsResponse(
            date_from=date_from,
            date_to=date_to,
            total_inbound_quantity=total_in,
            total_outbound_quantity=total_out,
            net_movement_quantity=total_in - total_out,
            total_movements_count=total_movements,
            breakdown_by_movement_type=type_breakdown,
            breakdown_by_category=cat_breakdown,
            breakdown_by_warehouse=wh_breakdown,
            timeline=timeline,
        )

    # =========================================================================
    # 11. INVENTORY AGING REPORT
    # =========================================================================
    async def get_inventory_aging_report(
        self,
        db: AsyncSession,
        warehouse_id: Optional[uuid.UUID] = None,
        aging_bucket: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[InventoryAgingReportItem], int, InventoryAgingReportSummary]:
        stmt = (
            select(
                StockBalance.product_id,
                Product.sku.label("product_sku"),
                Product.name.label("product_name"),
                StockBalance.warehouse_id,
                Warehouse.code.label("warehouse_code"),
                func.coalesce(func.sum(StockBalance.available_quantity), 0).label("quantity_on_hand"),
                func.max(StockBalance.last_calculated).label("last_updated"),
            )
            .select_from(StockBalance)
            .join(Product, StockBalance.product_id == Product.id)
            .join(Warehouse, StockBalance.warehouse_id == Warehouse.id)
            .group_by(
                StockBalance.product_id,
                Product.sku,
                Product.name,
                StockBalance.warehouse_id,
                Warehouse.code,
            )
        )

        filters = []
        if warehouse_id:
            filters.append(StockBalance.warehouse_id == warehouse_id)
        if search:
            patt = f"%{search}%"
            filters.append(or_(Product.sku.ilike(patt), Product.name.ilike(patt)))
        if filters:
            stmt = stmt.where(and_(*filters))

        res = await db.execute(stmt.order_by(Product.sku.asc()))
        rows = res.all()

        now = datetime.now(timezone.utc)
        items: List[InventoryAgingReportItem] = []
        b0_30 = Decimal("0.0")
        b31_60 = Decimal("0.0")
        b61_90 = Decimal("0.0")
        b90_plus = Decimal("0.0")
        total_qty = Decimal("0.0")

        for r in rows:
            qty = Decimal(str(r.quantity_on_hand))
            total_qty += qty

            # Query last inbound ledger entry
            in_stmt = (
                select(StockLedger.transaction_date)
                .where(
                    StockLedger.product_id == r.product_id,
                    StockLedger.warehouse_id == r.warehouse_id,
                    func.upper(StockLedger.direction) == "IN",
                )
                .order_by(StockLedger.transaction_date.desc())
                .limit(1)
            )
            last_in_date = (await db.execute(in_stmt)).scalar_one_or_none()

            # Query last movement of any direction
            mov_stmt = (
                select(StockLedger.transaction_date)
                .where(
                    StockLedger.product_id == r.product_id,
                    StockLedger.warehouse_id == r.warehouse_id,
                )
                .order_by(StockLedger.transaction_date.desc())
                .limit(1)
            )
            last_mov_date = (await db.execute(mov_stmt)).scalar_one_or_none()

            days_inbound = None
            if last_in_date:
                in_dt = last_in_date if last_in_date.tzinfo else last_in_date.replace(tzinfo=timezone.utc)
                days_inbound = max(0, (now - in_dt).days)

            days_mov = None
            if last_mov_date:
                m_dt = last_mov_date if last_mov_date.tzinfo else last_mov_date.replace(tzinfo=timezone.utc)
                days_mov = max(0, (now - m_dt).days)

            eval_days = days_inbound if days_inbound is not None else (days_mov if days_mov is not None else 0)

            if eval_days <= 30:
                bucket = "0-30 days"
                b0_30 += qty
            elif eval_days <= 60:
                bucket = "31-60 days"
                b31_60 += qty
            elif eval_days <= 90:
                bucket = "61-90 days"
                b61_90 += qty
            else:
                bucket = "90+ days"
                b90_plus += qty

            if aging_bucket and bucket.lower() != aging_bucket.lower():
                continue

            items.append(
                InventoryAgingReportItem(
                    product_id=r.product_id,
                    product_sku=r.product_sku,
                    product_name=r.product_name,
                    warehouse_id=r.warehouse_id,
                    warehouse_code=r.warehouse_code,
                    quantity_on_hand=qty,
                    last_inbound_date=last_in_date,
                    days_since_last_inbound=days_inbound,
                    last_movement_date=last_mov_date,
                    days_since_last_movement=days_mov,
                    aging_bucket=bucket,
                )
            )

        total_records = len(items)
        paginated_items = items[skip : skip + limit]

        summary = InventoryAgingReportSummary(
            total_products_count=len(rows),
            total_quantity_on_hand=total_qty,
            bucket_0_30_quantity=b0_30,
            bucket_31_60_quantity=b31_60,
            bucket_61_90_quantity=b61_90,
            bucket_90_plus_quantity=b90_plus,
        )

        return paginated_items, total_records, summary

    # =========================================================================
    # 12. EXECUTIVE DASHBOARD SUMMARY
    # =========================================================================
    async def get_dashboard_summary(
        self,
        db: AsyncSession,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> InventoryExecutiveDashboardResponse:
        now = datetime.now(timezone.utc)

        # 1. Total products and warehouses
        tot_prods = (await db.execute(select(func.count(Product.id)).where(Product.status != "Archived"))).scalar() or 0
        tot_whs = (await db.execute(select(func.count(Warehouse.id)).where(Warehouse.is_active == True))).scalar() or 0

        # 2. Stock balances
        bal_res = (
            await db.execute(
                select(
                    func.count(StockBalance.id),
                    func.coalesce(func.sum(StockBalance.available_quantity), 0),
                    func.coalesce(func.sum(StockBalance.reserved_quantity), 0),
                )
            )
        ).one()
        tot_lines = bal_res[0] or 0
        tot_on_hand = Decimal(str(bal_res[1] or 0))
        tot_reserved = Decimal(str(bal_res[2] or 0))
        tot_available = tot_on_hand - tot_reserved

        # 3. Low stock count
        low_stock_count = (
            await db.execute(
                select(func.count(distinct(StockBalance.product_id)))
                .select_from(StockBalance)
                .join(Product, StockBalance.product_id == Product.id)
                .where(Product.reorder_level > 0, StockBalance.available_quantity <= Product.reorder_level)
            )
        ).scalar() or 0

        # 4. Batches
        exp_count = (
            await db.execute(
                select(func.count(Batch.id)).where(
                    Batch.expiry_date.isnot(None),
                    Batch.expiry_date < now,
                )
            )
        ).scalar() or 0

        exp_soon_count = (
            await db.execute(
                select(func.count(Batch.id)).where(
                    Batch.expiry_date.isnot(None),
                    Batch.expiry_date >= now,
                    Batch.expiry_date <= now + timedelta(days=30),
                )
            )
        ).scalar() or 0

        # 5. Active Reservations
        active_res_count = (
            await db.execute(
                select(func.count(StockReservation.id)).where(StockReservation.status == "Active")
            )
        ).scalar() or 0

        # 6. Period Movements
        mov_filters = []
        if date_from:
            mov_filters.append(StockLedger.transaction_date >= date_from)
        if date_to:
            mov_filters.append(StockLedger.transaction_date <= date_to)

        sum_in = func.coalesce(
            func.sum(case((func.upper(StockLedger.direction) == "IN", StockLedger.quantity), else_=0)), 0
        )
        sum_out = func.coalesce(
            func.sum(case((func.upper(StockLedger.direction) == "OUT", StockLedger.quantity), else_=0)), 0
        )
        p_mov_stmt = select(func.count(StockLedger.id), sum_in, sum_out)
        if mov_filters:
            p_mov_stmt = p_mov_stmt.where(and_(*mov_filters))
        p_res = (await db.execute(p_mov_stmt)).one()
        p_count = p_res[0] or 0
        p_in = Decimal(str(p_res[1] or 0))
        p_out = Decimal(str(p_res[2] or 0))

        # 7. Warehouse Breakdown
        wh_rows = (
            await db.execute(
                select(
                    Warehouse.id,
                    Warehouse.code,
                    Warehouse.name,
                    func.count(distinct(StockBalance.product_id)),
                    func.coalesce(func.sum(StockBalance.available_quantity), 0),
                    func.coalesce(func.sum(StockBalance.reserved_quantity), 0),
                )
                .select_from(Warehouse)
                .outerjoin(StockBalance, Warehouse.id == StockBalance.warehouse_id)
                .where(Warehouse.is_active == True)
                .group_by(Warehouse.id, Warehouse.code, Warehouse.name)
            )
        ).all()

        wh_summaries = [
            WarehouseUtilizationSummary(
                warehouse_id=r[0],
                warehouse_code=r[1],
                warehouse_name=r[2],
                total_products_count=r[3] or 0,
                total_on_hand_quantity=Decimal(str(r[4] or 0)),
                total_reserved_quantity=Decimal(str(r[5] or 0)),
                total_available_quantity=Decimal(str(r[4] or 0)) - Decimal(str(r[5] or 0)),
            )
            for r in wh_rows
        ]

        # 8. Top moving products
        top_mov_stmt = (
            select(
                StockLedger.product_id,
                Product.sku,
                Product.name,
                func.coalesce(func.sum(StockLedger.quantity), 0).label("moved_qty"),
                func.count(StockLedger.id).label("m_count"),
                StockLedger.direction,
            )
            .select_from(StockLedger)
            .join(Product, StockLedger.product_id == Product.id)
            .group_by(StockLedger.product_id, Product.sku, Product.name, StockLedger.direction)
            .order_by(func.sum(StockLedger.quantity).desc())
            .limit(10)
        )
        if mov_filters:
            top_mov_stmt = top_mov_stmt.where(and_(*mov_filters))
        top_mov_res = (await db.execute(top_mov_stmt)).all()

        top_moving = [
            TopMovingProductItem(
                product_id=r[0],
                product_sku=r[1],
                product_name=r[2],
                total_moved_quantity=Decimal(str(r[3])),
                movement_count=r[4],
                direction=r[5],
            )
            for r in top_mov_res
        ]

        return InventoryExecutiveDashboardResponse(
            as_of_timestamp=now,
            total_products_tracked=tot_prods,
            total_warehouses_count=tot_whs,
            total_stock_lines=tot_lines,
            total_on_hand_quantity=tot_on_hand,
            total_reserved_quantity=tot_reserved,
            total_available_quantity=tot_available,
            low_stock_products_count=low_stock_count,
            expired_batches_count=exp_count,
            expiring_soon_batches_count=exp_soon_count,
            active_reservations_count=active_res_count,
            period_inbound_quantity=p_in,
            period_outbound_quantity=p_out,
            period_movement_count=p_count,
            warehouse_stock_breakdown=wh_summaries,
            top_moving_products=top_moving,
        )


inventory_report_repository = InventoryReportRepository()
