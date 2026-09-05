from datetime import datetime
from decimal import Decimal
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator


# ============================================================================
# BATCH SCHEMAS
# ============================================================================
class BatchCreate(BaseModel):
    batch_number: str = Field(..., max_length=100, description="Unique batch identification code")
    product_id: uuid.UUID
    manufacturing_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    supplier_batch_ref: Optional[str] = Field(None, max_length=100)
    supplier_reference: Optional[str] = Field(None, max_length=100)
    current_quantity: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"))
    status: Optional[str] = Field(default="Active", max_length=20)
    notes: Optional[str] = None
    remarks: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def sync_batch_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "supplier_reference" in data and data["supplier_reference"] is not None and not data.get("supplier_batch_ref"):
                data["supplier_batch_ref"] = data["supplier_reference"]
            elif "supplier_batch_ref" in data and data["supplier_batch_ref"] is not None and not data.get("supplier_reference"):
                data["supplier_reference"] = data["supplier_batch_ref"]
            if "notes" in data and data["notes"] is not None and not data.get("remarks"):
                data["remarks"] = data["notes"]
            elif "remarks" in data and data["remarks"] is not None and not data.get("notes"):
                data["notes"] = data["remarks"]
        return data


class BatchUpdate(BaseModel):
    manufacturing_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    supplier_batch_ref: Optional[str] = None
    supplier_reference: Optional[str] = None
    current_quantity: Optional[Decimal] = Field(None, ge=Decimal("0.0"))
    status: Optional[str] = None
    notes: Optional[str] = None
    remarks: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def sync_batch_update_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "supplier_reference" in data and data["supplier_reference"] is not None and not data.get("supplier_batch_ref"):
                data["supplier_batch_ref"] = data["supplier_reference"]
            elif "supplier_batch_ref" in data and data["supplier_batch_ref"] is not None and not data.get("supplier_reference"):
                data["supplier_reference"] = data["supplier_batch_ref"]
            if "notes" in data and data["notes"] is not None and not data.get("remarks"):
                data["remarks"] = data["notes"]
            elif "remarks" in data and data["remarks"] is not None and not data.get("notes"):
                data["notes"] = data["remarks"]
        return data


class BatchResponse(BaseModel):
    id: uuid.UUID
    batch_number: str
    product_id: uuid.UUID
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    manufacturing_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    supplier_batch_ref: Optional[str] = None
    supplier_reference: Optional[str] = None
    current_quantity: Decimal
    status: str
    notes: Optional[str] = None
    remarks: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def populate_batch_aliases(cls, data: Any) -> Any:
        if hasattr(data, "supplier_batch_ref") and not hasattr(data, "supplier_reference"):
            data.supplier_reference = data.supplier_batch_ref
        elif isinstance(data, dict):
            if "supplier_batch_ref" in data and not data.get("supplier_reference"):
                data["supplier_reference"] = data["supplier_batch_ref"]
            if "remarks" in data and not data.get("notes"):
                data["notes"] = data["remarks"]
        return data


class PaginatedBatchResponse(BaseModel):
    items: List[BatchResponse]
    total: int
    page: int
    size: int
    pages: int


# ============================================================================
# SERIAL NUMBER SCHEMAS
# ============================================================================
class SerialNumberCreate(BaseModel):
    serial_number: str = Field(..., max_length=100, description="Globally unique serial number string")
    product_id: uuid.UUID
    warehouse_id: Optional[uuid.UUID] = None
    storage_location_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None
    status: Optional[str] = Field(default="Available", max_length=20)


class SerialNumberUpdate(BaseModel):
    warehouse_id: Optional[uuid.UUID] = None
    storage_location_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None
    status: Optional[str] = None


class SerialNumberResponse(BaseModel):
    id: uuid.UUID
    serial_number: str
    product_id: uuid.UUID
    product_sku: Optional[str] = None
    warehouse_id: Optional[uuid.UUID] = None
    warehouse_code: Optional[str] = None
    storage_location_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None
    status: str
    history: Optional[List[Dict[str, Any]]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedSerialNumberResponse(BaseModel):
    items: List[SerialNumberResponse]
    total: int
    page: int
    size: int
    pages: int


# ============================================================================
# LOT SCHEMAS
# ============================================================================
class LotCreate(BaseModel):
    lot_number: str = Field(..., max_length=100)
    product_id: uuid.UUID
    production_lot: Optional[str] = Field(None, max_length=100)
    supplier_lot: Optional[str] = Field(None, max_length=100)
    traceability_data: Optional[Dict[str, Any]] = None


class LotUpdate(BaseModel):
    production_lot: Optional[str] = None
    supplier_lot: Optional[str] = None
    traceability_data: Optional[Dict[str, Any]] = None


class LotResponse(BaseModel):
    id: uuid.UUID
    lot_number: str
    product_id: uuid.UUID
    product_sku: Optional[str] = None
    production_lot: Optional[str] = None
    supplier_lot: Optional[str] = None
    traceability_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedLotResponse(BaseModel):
    items: List[LotResponse]
    total: int
    page: int
    size: int
    pages: int


# ============================================================================
# STOCK RESERVATION SCHEMAS
# ============================================================================
class StockReservationCreate(BaseModel):
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    storage_location_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None
    quantity: Decimal = Field(..., gt=Decimal("0.0"))
    reserved_for_type: Optional[str] = Field("Sales", max_length=50, description="Sales, Manufacturing, Procurement, Internal")
    reference_type: Optional[str] = Field(None, max_length=50)
    reserved_for_id: Optional[uuid.UUID] = None
    reference_id: Optional[uuid.UUID] = None
    expires_at: Optional[datetime] = None
    remarks: Optional[str] = None
    notes: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def sync_res_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "reference_type" in data and data["reference_type"] is not None and not data.get("reserved_for_type"):
                data["reserved_for_type"] = data["reference_type"]
            elif "reserved_for_type" in data and data["reserved_for_type"] is not None and not data.get("reference_type"):
                data["reference_type"] = data["reserved_for_type"]
            if "reference_id" in data and data["reference_id"] is not None and not data.get("reserved_for_id"):
                data["reserved_for_id"] = data["reference_id"]
            elif "reserved_for_id" in data and data["reserved_for_id"] is not None and not data.get("reference_id"):
                data["reference_id"] = data["reserved_for_id"]
            if "notes" in data and data["notes"] is not None and not data.get("remarks"):
                data["remarks"] = data["notes"]
            elif "remarks" in data and data["remarks"] is not None and not data.get("notes"):
                data["notes"] = data["remarks"]
        return data


class StockReservationConsumeRequest(BaseModel):
    quantity: Optional[Decimal] = Field(None, gt=Decimal("0.0"), description="Quantity to consume (defaults to full reservation qty)")
    issue_id: Optional[uuid.UUID] = Field(None, description="Optional linked GoodsIssue document ID")
    notes: Optional[str] = None


class StockReservationResponse(BaseModel):
    id: uuid.UUID
    reservation_number: str
    product_id: uuid.UUID
    product_sku: Optional[str] = None
    warehouse_id: uuid.UUID
    warehouse_code: Optional[str] = None
    storage_location_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None
    quantity: Decimal
    reserved_for_type: str
    reference_type: Optional[str] = None
    reserved_for_id: Optional[uuid.UUID] = None
    reference_id: Optional[uuid.UUID] = None
    status: str
    expires_at: Optional[datetime] = None
    released_at: Optional[datetime] = None
    consumed_at: Optional[datetime] = None
    remarks: Optional[str] = None
    notes: Optional[str] = None
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def populate_res_aliases(cls, data: Any) -> Any:
        if hasattr(data, "reserved_for_type") and not hasattr(data, "reference_type"):
            data.reference_type = data.reserved_for_type
        if hasattr(data, "reserved_for_id") and not hasattr(data, "reference_id"):
            data.reference_id = data.reserved_for_id
        if hasattr(data, "remarks") and not hasattr(data, "notes"):
            data.notes = data.remarks
        elif isinstance(data, dict):
            if "reserved_for_type" in data and not data.get("reference_type"):
                data["reference_type"] = data["reserved_for_type"]
            if "reserved_for_id" in data and not data.get("reference_id"):
                data["reference_id"] = data["reserved_for_id"]
            if "remarks" in data and not data.get("notes"):
                data["notes"] = data["remarks"]
        return data


class PaginatedStockReservationResponse(BaseModel):
    items: List[StockReservationResponse]
    total: int
    page: int
    size: int
    pages: int


# ============================================================================
# CYCLE COUNT SCHEMAS
# ============================================================================
class CycleCountItemCreate(BaseModel):
    product_id: uuid.UUID
    batch_id: Optional[uuid.UUID] = None
    counted_qty: Decimal = Field(..., ge=Decimal("0.0"))
    remarks: Optional[str] = None


class CycleCountCreate(BaseModel):
    warehouse_id: uuid.UUID
    storage_location_id: Optional[uuid.UUID] = None
    planned_date: Optional[datetime] = None
    notes: Optional[str] = None
    items: List[CycleCountItemCreate] = Field(default_factory=list)


class CycleCountItemResponse(BaseModel):
    id: uuid.UUID
    cycle_count_id: uuid.UUID
    product_id: uuid.UUID
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    batch_id: Optional[uuid.UUID] = None
    system_qty: Decimal
    counted_qty: Decimal
    variance_qty: Decimal
    remarks: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CycleCountResponse(BaseModel):
    id: uuid.UUID
    count_number: str
    warehouse_id: uuid.UUID
    warehouse_name: Optional[str] = None
    storage_location_id: Optional[uuid.UUID] = None
    status: str
    planned_date: Optional[datetime] = None
    counted_by_id: Optional[uuid.UUID] = None
    approved_by_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    items: List[CycleCountItemResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedCycleCountResponse(BaseModel):
    items: List[CycleCountResponse]
    total: int
    page: int
    size: int
    pages: int


# ============================================================================
# REPORT & ANALYTICS SCHEMAS
# ============================================================================
class StockValuationItem(BaseModel):
    product_id: uuid.UUID
    sku: str
    product_name: str
    warehouse_id: uuid.UUID
    warehouse_code: str
    quantity: Decimal
    estimated_unit_cost: Decimal
    total_valuation: Decimal


class InventoryAgingItem(BaseModel):
    product_id: uuid.UUID
    sku: str
    product_name: str
    warehouse_code: str
    quantity: Decimal
    days_in_stock: int
    aging_bucket: str  # 0-30, 31-60, 61-90, 90+


class MovementAnalysisItem(BaseModel):
    product_id: uuid.UUID
    sku: str
    product_name: str
    total_issues: Decimal
    movement_category: str  # Fast Moving, Slow Moving, Dead Stock


class InventoryDashboardSummary(BaseModel):
    total_inventory_value: Decimal
    total_items_count: Decimal
    turnover_ratio: Decimal
    warehouse_utilization_pct: Decimal
    reserved_stock_qty: Decimal
    available_stock_qty: Decimal
    expiring_stock_qty: Decimal
    top_moving_products: List[Dict[str, Any]] = Field(default_factory=list)
    warehouse_stock_breakdown: List[Dict[str, Any]] = Field(default_factory=list)


# ============================================================================
# GLOBAL SEARCH SCHEMAS
# ============================================================================
class SearchResultItem(BaseModel):
    entity_type: str  # Product, Batch, SerialNumber, Lot, Warehouse, StorageLocation
    entity_id: uuid.UUID
    title: str
    subtitle: Optional[str] = None
    sku_or_code: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class GlobalSearchResponse(BaseModel):
    query: str
    total_results: int
    results: List[SearchResultItem]


# ============================================================================
# IMPORT / EXPORT SCHEMAS
# ============================================================================
class ImportResult(BaseModel):
    entity_type: str
    total_records: int
    imported_count: int
    failed_count: int
    errors: List[str] = Field(default_factory=list)
