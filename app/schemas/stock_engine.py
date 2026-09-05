from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


# --- Transaction Types ---

class InventoryTransactionTypeBase(BaseModel):
    code: str = Field(..., max_length=50, description="Unique code (e.g. OPENING_STOCK)")
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    direction: str = Field(..., max_length=20, description="IN, OUT, TRANSFER, ADJUSTMENT, SYSTEM")
    is_active: bool = True


class InventoryTransactionTypeCreate(InventoryTransactionTypeBase):
    pass


class InventoryTransactionTypeResponse(InventoryTransactionTypeBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Generic Stock Movements (Milestone v0.6.1) ---

class StockMovementCreate(BaseModel):
    """
    Schema for creating generic stock movements: STOCK_IN, STOCK_OUT, ADJUSTMENT.
    """
    product_id: uuid.UUID = Field(..., description="Target Product master record UUID")
    warehouse_id: uuid.UUID = Field(..., description="Target Warehouse facility UUID")
    storage_location_id: Optional[uuid.UUID] = Field(None, description="Optional target storage location (Rack/Shelf/Bin) UUID")
    movement_type: str = Field(
        "STOCK_IN",
        description="Movement semantic type: STOCK_IN, STOCK_OUT, ADJUSTMENT",
    )
    direction: Optional[str] = Field(
        None,
        description="Explicit direction: IN, OUT. Inferred automatically if omitted for STOCK_IN / STOCK_OUT.",
    )
    quantity: Decimal = Field(
        ...,
        gt=Decimal("0.0"),
        description="Movement quantity magnitude (must be strictly positive > 0)",
    )
    idempotency_key: Optional[str] = Field(
        None,
        max_length=255,
        description="Optional unique key to ensure idempotent movement processing",
    )
    reference_type: Optional[str] = Field(
        None,
        max_length=100,
        description="Optional upstream document type (e.g. Manual, OpeningStock, Adjustment)",
    )
    reference_id: Optional[uuid.UUID] = Field(
        None,
        description="Optional upstream document UUID",
    )
    batch_id: Optional[uuid.UUID] = Field(
        None,
        description="Optional associated batch ID for batch-tracked products",
    )
    serial_numbers: Optional[List[str]] = Field(
        None,
        description="Optional list of serial numbers for serial-tracked movements",
    )
    reason: Optional[str] = Field(
        None,
        max_length=255,
        description="Business reason for movement",
    )
    notes: Optional[str] = Field(
        None,
        description="Descriptive notes or remarks",
    )
    metadata_json: Optional[Dict[str, Any]] = Field(
        None,
        description="Extensible JSON metadata",
    )


class StockMovementResponse(BaseModel):
    """
    Response schema for stock movements and ledger transactions.
    """
    id: uuid.UUID
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    storage_location_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None
    movement_type: str
    direction: str
    quantity: Decimal
    quantity_before: Decimal
    quantity_after: Decimal
    running_balance: Decimal
    transaction_type_id: Optional[uuid.UUID] = None
    unit_id: Optional[uuid.UUID] = None
    unit_of_measure_id: Optional[uuid.UUID] = None
    reference_type: Optional[str] = None
    reference_id: Optional[uuid.UUID] = None
    idempotency_key: Optional[str] = None
    reason: Optional[str] = None
    notes: Optional[str] = None
    remarks: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    transaction_date: datetime
    created_by: Optional[uuid.UUID] = None
    created_at: datetime

    # Display names
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    warehouse_code: Optional[str] = None
    warehouse_name: Optional[str] = None
    storage_location_code: Optional[str] = None
    batch_number: Optional[str] = None
    transaction_type_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedStockMovementResponse(BaseModel):
    items: List[StockMovementResponse]
    total: int
    skip: int
    limit: int


# --- Stock Ledger ---

class StockLedgerResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    storage_location_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None
    movement_type: str = "STOCK_IN"
    direction: str
    quantity: Decimal
    quantity_before: Decimal = Decimal("0.0")
    quantity_after: Decimal = Decimal("0.0")
    running_balance: Decimal
    transaction_type_id: Optional[uuid.UUID] = None
    unit_id: Optional[uuid.UUID] = None
    unit_of_measure_id: Optional[uuid.UUID] = None
    reference_type: Optional[str] = None
    reference_id: Optional[uuid.UUID] = None
    idempotency_key: Optional[str] = None
    reason: Optional[str] = None
    notes: Optional[str] = None
    remarks: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    transaction_date: datetime
    created_by: Optional[uuid.UUID] = None
    created_at: datetime

    # Nested display names
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    warehouse_code: Optional[str] = None
    warehouse_name: Optional[str] = None
    storage_location_code: Optional[str] = None
    batch_number: Optional[str] = None
    transaction_type_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedStockLedgerResponse(BaseModel):
    items: List[StockLedgerResponse]
    total: int
    skip: int
    limit: int


# --- Stock Balance Projections ---

class StockBalanceResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    storage_location_id: Optional[uuid.UUID] = None
    available_quantity: Decimal
    quantity_on_hand: Decimal = Decimal("0.0")
    reserved_quantity: Decimal = Decimal("0.0")
    damaged_quantity: Decimal = Decimal("0.0")
    in_transit_quantity: Decimal = Decimal("0.0")
    total_quantity: Decimal = Decimal("0.0")
    last_calculated: datetime

    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    warehouse_code: Optional[str] = None
    warehouse_name: Optional[str] = None
    storage_location_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedStockBalanceResponse(BaseModel):
    items: List[StockBalanceResponse]
    total: int
    skip: int
    limit: int


class WarehouseStockSummaryResponse(BaseModel):
    warehouse_id: uuid.UUID
    warehouse_code: str
    warehouse_name: str
    total_products: int
    total_available_stock: Decimal
    total_reserved_stock: Decimal
    total_damaged_stock: Decimal


class ProductStockSummaryResponse(BaseModel):
    product_id: uuid.UUID
    sku: str
    product_name: str
    total_available_stock: Decimal
    total_reserved_stock: Decimal
    total_damaged_stock: Decimal
    warehouse_balances: List[StockBalanceResponse] = []


class StorageLocationStockSummaryResponse(BaseModel):
    storage_location_id: uuid.UUID
    storage_location_code: str
    warehouse_id: uuid.UUID
    warehouse_code: str
    total_products: int
    total_available_stock: Decimal
    balances: List[StockBalanceResponse] = []


# --- Opening Stock ---

class OpeningStockCreate(BaseModel):
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    location_id: Optional[uuid.UUID] = None
    quantity: Decimal = Field(..., gt=0, description="Initial stock quantity to onboard")
    reference_number: str = Field(..., max_length=100)


class OpeningStockResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    location_id: Optional[uuid.UUID] = None
    quantity: Decimal
    reference_number: str
    created_by: Optional[uuid.UUID] = None
    approved_by: Optional[uuid.UUID] = None
    created_at: datetime

    product_sku: Optional[str] = None
    warehouse_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# --- Inventory Adjustments ---

class InventoryAdjustmentCreate(BaseModel):
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    location_id: Optional[uuid.UUID] = None
    adjustment_type: str = Field(..., description="Increase or Decrease")
    reason: str = Field(..., min_length=3, max_length=255)
    actual_quantity: Decimal = Field(..., ge=0, description="Physically counted stock quantity")


class InventoryAdjustmentUpdate(BaseModel):
    reason: Optional[str] = Field(None, min_length=3, max_length=255)
    actual_quantity: Optional[Decimal] = Field(None, ge=0)


class InventoryAdjustmentResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    location_id: Optional[uuid.UUID] = None
    adjustment_type: str
    reason: str
    expected_quantity: Decimal
    actual_quantity: Decimal
    difference: Decimal
    status: str
    created_by: Optional[uuid.UUID] = None
    approved_by: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    warehouse_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
