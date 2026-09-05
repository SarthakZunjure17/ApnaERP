from datetime import datetime
from decimal import Decimal
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# 1. CURRENT STOCK / STOCK BALANCE REPORT SCHEMAS
# ============================================================================
class StockReportItem(BaseModel):
    product_id: uuid.UUID
    product_sku: str
    product_name: str
    category_id: Optional[uuid.UUID] = None
    category_name: Optional[str] = None
    uom_symbol: Optional[str] = None
    tracking_type: str = "NONE"
    warehouse_id: uuid.UUID
    warehouse_code: str
    warehouse_name: str
    storage_location_id: Optional[uuid.UUID] = None
    storage_location_code: Optional[str] = None
    storage_location_name: Optional[str] = None
    quantity_on_hand: Decimal
    reserved_quantity: Decimal
    available_quantity: Decimal
    damaged_quantity: Decimal = Decimal("0.0")
    in_transit_quantity: Decimal = Decimal("0.0")
    last_updated: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class StockReportSummary(BaseModel):
    total_products_count: int
    total_records_count: int
    total_quantity_on_hand: Decimal
    total_reserved_quantity: Decimal
    total_available_quantity: Decimal


class PaginatedStockReportResponse(BaseModel):
    items: List[StockReportItem]
    total: int
    page: int
    size: int
    pages: int
    summary: StockReportSummary


# ============================================================================
# 2. STOCK MOVEMENT REPORT SCHEMAS
# ============================================================================
class StockMovementReportItem(BaseModel):
    movement_id: uuid.UUID
    transaction_date: datetime
    product_id: uuid.UUID
    product_sku: str
    product_name: str
    warehouse_id: uuid.UUID
    warehouse_code: str
    storage_location_id: Optional[uuid.UUID] = None
    storage_location_code: Optional[str] = None
    movement_type: str
    direction: str
    quantity: Decimal
    quantity_before: Decimal
    quantity_after: Decimal
    running_balance: Decimal
    reference_type: Optional[str] = None
    reference_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None
    batch_number: Optional[str] = None
    serial_numbers: Optional[List[str]] = None
    reason: Optional[str] = None
    notes: Optional[str] = None
    created_by: Optional[uuid.UUID] = None

    model_config = ConfigDict(from_attributes=True)


class StockMovementReportSummary(BaseModel):
    total_movements_count: int
    total_inbound_quantity: Decimal
    total_outbound_quantity: Decimal
    net_movement_quantity: Decimal


class PaginatedStockMovementReportResponse(BaseModel):
    items: List[StockMovementReportItem]
    total: int
    page: int
    size: int
    pages: int
    summary: StockMovementReportSummary


# ============================================================================
# 3. WAREHOUSE INVENTORY REPORT SCHEMAS
# ============================================================================
class WarehouseInventoryReportItem(BaseModel):
    warehouse_id: uuid.UUID
    warehouse_code: str
    warehouse_name: str
    is_active: bool
    total_products_stocked: int
    total_storage_locations: int
    total_on_hand_quantity: Decimal
    total_reserved_quantity: Decimal
    total_available_quantity: Decimal
    active_tracked_batches_count: int
    tracked_serials_count: int
    expired_batches_count: int
    low_stock_items_count: int

    model_config = ConfigDict(from_attributes=True)


class PaginatedWarehouseInventoryReportResponse(BaseModel):
    items: List[WarehouseInventoryReportItem]
    total: int
    page: int
    size: int
    pages: int


# ============================================================================
# 4. PRODUCT INVENTORY REPORT SCHEMAS
# ============================================================================
class ProductInventoryReportItem(BaseModel):
    product_id: uuid.UUID
    product_sku: str
    product_name: str
    category_id: Optional[uuid.UUID] = None
    category_name: Optional[str] = None
    uom_symbol: Optional[str] = None
    tracking_type: str
    is_active: bool
    status: str
    total_on_hand: Decimal
    total_reserved: Decimal
    total_available: Decimal
    warehouses_count: int
    locations_count: int
    batches_count: int
    serials_count: int
    recent_movement_quantity: Decimal
    last_movement_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedProductInventoryReportResponse(BaseModel):
    items: List[ProductInventoryReportItem]
    total: int
    page: int
    size: int
    pages: int


# ============================================================================
# 5. BATCH & EXPIRY REPORT SCHEMAS
# ============================================================================
class BatchExpiryReportItem(BaseModel):
    batch_id: uuid.UUID
    batch_number: str
    product_id: uuid.UUID
    product_sku: str
    product_name: str
    manufacturing_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    days_until_expiry: Optional[int] = None
    supplier_batch_ref: Optional[str] = None
    current_quantity: Decimal
    status: str  # Active, Expired, Consumed
    expiry_status: str  # Expired, Expiring Soon, Normal, No Expiry
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BatchExpiryReportSummary(BaseModel):
    total_batches_count: int
    active_batches_count: int
    expired_batches_count: int
    expiring_soon_batches_count: int
    total_batch_stock_quantity: Decimal
    expired_stock_quantity: Decimal


class PaginatedBatchExpiryReportResponse(BaseModel):
    items: List[BatchExpiryReportItem]
    total: int
    page: int
    size: int
    pages: int
    summary: BatchExpiryReportSummary


# ============================================================================
# 6. SERIAL INVENTORY REPORT SCHEMAS
# ============================================================================
class SerialInventoryReportItem(BaseModel):
    serial_id: uuid.UUID
    serial_number: str
    product_id: uuid.UUID
    product_sku: str
    product_name: str
    batch_id: Optional[uuid.UUID] = None
    batch_number: Optional[str] = None
    warehouse_id: Optional[uuid.UUID] = None
    warehouse_code: Optional[str] = None
    storage_location_id: Optional[uuid.UUID] = None
    storage_location_code: Optional[str] = None
    status: str  # Available, Reserved, Issued, Returned, Scrapped, Lost
    history_events_count: int
    last_event: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedSerialInventoryReportResponse(BaseModel):
    items: List[SerialInventoryReportItem]
    total: int
    page: int
    size: int
    pages: int


# ============================================================================
# 7. STOCK RESERVATION REPORT SCHEMAS
# ============================================================================
class StockReservationReportItem(BaseModel):
    reservation_id: uuid.UUID
    reservation_number: str
    product_id: uuid.UUID
    product_sku: str
    product_name: str
    warehouse_id: uuid.UUID
    warehouse_code: str
    storage_location_id: Optional[uuid.UUID] = None
    storage_location_code: Optional[str] = None
    batch_id: Optional[uuid.UUID] = None
    batch_number: Optional[str] = None
    quantity: Decimal
    reserved_for_type: str
    reference_type: Optional[str] = None
    reserved_for_id: Optional[uuid.UUID] = None
    reference_id: Optional[uuid.UUID] = None
    status: str  # Active, Released, Consumed, Cancelled
    expires_at: Optional[datetime] = None
    released_at: Optional[datetime] = None
    consumed_at: Optional[datetime] = None
    remarks: Optional[str] = None
    notes: Optional[str] = None
    created_by: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StockReservationReportSummary(BaseModel):
    total_reservations_count: int
    active_reservations_count: int
    released_reservations_count: int
    consumed_reservations_count: int
    total_active_reserved_quantity: Decimal


class PaginatedStockReservationReportResponse(BaseModel):
    items: List[StockReservationReportItem]
    total: int
    page: int
    size: int
    pages: int
    summary: StockReservationReportSummary


# ============================================================================
# 8. AVAILABLE STOCK REPORT SCHEMAS
# ============================================================================
class AvailableStockReportItem(BaseModel):
    product_id: uuid.UUID
    product_sku: str
    product_name: str
    tracking_type: str
    warehouse_id: uuid.UUID
    warehouse_code: str
    storage_location_id: Optional[uuid.UUID] = None
    storage_location_code: Optional[str] = None
    batch_id: Optional[uuid.UUID] = None
    batch_number: Optional[str] = None
    on_hand_quantity: Decimal
    reserved_quantity: Decimal
    available_quantity: Decimal

    model_config = ConfigDict(from_attributes=True)


class PaginatedAvailableStockReportResponse(BaseModel):
    items: List[AvailableStockReportItem]
    total: int
    page: int
    size: int
    pages: int


# ============================================================================
# 9. LOW STOCK / REORDER REPORT SCHEMAS
# ============================================================================
class LowStockReportItem(BaseModel):
    product_id: uuid.UUID
    product_sku: str
    product_name: str
    category_id: Optional[uuid.UUID] = None
    category_name: Optional[str] = None
    warehouse_id: Optional[uuid.UUID] = None
    warehouse_code: Optional[str] = None
    on_hand_quantity: Decimal
    reorder_level: Decimal
    reorder_quantity: Decimal
    minimum_stock: Decimal
    maximum_stock: Optional[Decimal] = None
    below_reorder_level: bool
    below_minimum_stock: bool
    shortage_quantity: Decimal

    model_config = ConfigDict(from_attributes=True)


class LowStockReportSummary(BaseModel):
    total_low_stock_items: int
    total_below_min_items: int
    total_shortage_quantity: Decimal


class PaginatedLowStockReportResponse(BaseModel):
    items: List[LowStockReportItem]
    total: int
    page: int
    size: int
    pages: int
    summary: LowStockReportSummary


# ============================================================================
# 10. INVENTORY MOVEMENT ANALYTICS SCHEMAS
# ============================================================================
class MovementAnalyticsCategoryBreakdown(BaseModel):
    category_id: Optional[uuid.UUID] = None
    category_name: str
    inbound_quantity: Decimal
    outbound_quantity: Decimal
    movement_count: int


class MovementAnalyticsWarehouseBreakdown(BaseModel):
    warehouse_id: uuid.UUID
    warehouse_code: str
    warehouse_name: str
    inbound_quantity: Decimal
    outbound_quantity: Decimal
    movement_count: int


class MovementAnalyticsTypeBreakdown(BaseModel):
    movement_type: str
    direction: str
    total_quantity: Decimal
    movement_count: int


class MovementAnalyticsTimelineBucket(BaseModel):
    period: str  # YYYY-MM-DD or YYYY-WW or YYYY-MM
    inbound_quantity: Decimal
    outbound_quantity: Decimal
    net_movement: Decimal
    movement_count: int


class InventoryMovementAnalyticsResponse(BaseModel):
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    total_inbound_quantity: Decimal
    total_outbound_quantity: Decimal
    net_movement_quantity: Decimal
    total_movements_count: int
    breakdown_by_movement_type: List[MovementAnalyticsTypeBreakdown] = Field(default_factory=list)
    breakdown_by_category: List[MovementAnalyticsCategoryBreakdown] = Field(default_factory=list)
    breakdown_by_warehouse: List[MovementAnalyticsWarehouseBreakdown] = Field(default_factory=list)
    timeline: List[MovementAnalyticsTimelineBucket] = Field(default_factory=list)


# ============================================================================
# 11. INVENTORY AGING REPORT SCHEMAS
# ============================================================================
class InventoryAgingReportItem(BaseModel):
    product_id: uuid.UUID
    product_sku: str
    product_name: str
    warehouse_id: uuid.UUID
    warehouse_code: str
    quantity_on_hand: Decimal
    last_inbound_date: Optional[datetime] = None
    days_since_last_inbound: Optional[int] = None
    last_movement_date: Optional[datetime] = None
    days_since_last_movement: Optional[int] = None
    aging_bucket: str  # 0-30 days, 31-60 days, 61-90 days, 90+ days

    model_config = ConfigDict(from_attributes=True)


class InventoryAgingReportSummary(BaseModel):
    total_products_count: int
    total_quantity_on_hand: Decimal
    bucket_0_30_quantity: Decimal
    bucket_31_60_quantity: Decimal
    bucket_61_90_quantity: Decimal
    bucket_90_plus_quantity: Decimal


class PaginatedInventoryAgingReportResponse(BaseModel):
    items: List[InventoryAgingReportItem]
    total: int
    page: int
    size: int
    pages: int
    summary: InventoryAgingReportSummary


# ============================================================================
# 12. EXECUTIVE DASHBOARD SUMMARY SCHEMAS
# ============================================================================
class TopMovingProductItem(BaseModel):
    product_id: uuid.UUID
    product_sku: str
    product_name: str
    total_moved_quantity: Decimal
    movement_count: int
    direction: str


class WarehouseUtilizationSummary(BaseModel):
    warehouse_id: uuid.UUID
    warehouse_code: str
    warehouse_name: str
    total_products_count: int
    total_on_hand_quantity: Decimal
    total_reserved_quantity: Decimal
    total_available_quantity: Decimal


class InventoryExecutiveDashboardResponse(BaseModel):
    as_of_timestamp: datetime
    total_products_tracked: int
    total_warehouses_count: int
    total_stock_lines: int
    total_on_hand_quantity: Decimal
    total_reserved_quantity: Decimal
    total_available_quantity: Decimal
    low_stock_products_count: int
    expired_batches_count: int
    expiring_soon_batches_count: int
    active_reservations_count: int
    period_inbound_quantity: Decimal
    period_outbound_quantity: Decimal
    period_movement_count: int
    warehouse_stock_breakdown: List[WarehouseUtilizationSummary] = Field(default_factory=list)
    top_moving_products: List[TopMovingProductItem] = Field(default_factory=list)
