from datetime import datetime
from decimal import Decimal
from typing import Optional, List
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


# --- Stock Ledger ---

class StockLedgerResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    storage_location_id: Optional[uuid.UUID] = None
    transaction_type_id: uuid.UUID
    reference_type: Optional[str] = None
    reference_id: Optional[uuid.UUID] = None
    quantity: Decimal
    unit_id: Optional[uuid.UUID] = None
    direction: str
    running_balance: Decimal
    transaction_date: datetime
    remarks: Optional[str] = None
    created_by: Optional[uuid.UUID] = None
    created_at: datetime

    # Nested display names
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    warehouse_code: Optional[str] = None
    warehouse_name: Optional[str] = None
    storage_location_code: Optional[str] = None
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
    reserved_quantity: Decimal
    damaged_quantity: Decimal
    in_transit_quantity: Decimal
    total_quantity: Decimal = Decimal("0.0")
    last_calculated: datetime

    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    warehouse_code: Optional[str] = None
    warehouse_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


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
