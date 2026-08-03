from datetime import datetime
from decimal import Decimal
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


# --- Goods Receipt Schemas ---

class GoodsReceiptItemCreate(BaseModel):
    product_id: uuid.UUID
    storage_location_id: Optional[uuid.UUID] = None
    quantity: Decimal = Field(..., gt=0, description="Quantity received (must be positive)")
    unit_id: Optional[uuid.UUID] = None
    unit_cost: Optional[Decimal] = Field(None, ge=0)
    remarks: Optional[str] = None


class GoodsReceiptItemResponse(BaseModel):
    id: uuid.UUID
    goods_receipt_id: uuid.UUID
    product_id: uuid.UUID
    storage_location_id: Optional[uuid.UUID] = None
    quantity: Decimal
    unit_id: Optional[uuid.UUID] = None
    unit_cost: Optional[Decimal] = None
    remarks: Optional[str] = None

    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    storage_location_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class GoodsReceiptCreate(BaseModel):
    receipt_number: str = Field(..., min_length=3, max_length=100)
    warehouse_id: uuid.UUID
    supplier_reference: Optional[str] = Field(None, max_length=100)
    external_reference: Optional[str] = Field(None, max_length=100)
    receipt_date: Optional[datetime] = None
    remarks: Optional[str] = None
    items: List[GoodsReceiptItemCreate] = Field(..., min_length=1)



class GoodsReceiptUpdate(BaseModel):
    supplier_reference: Optional[str] = Field(None, max_length=100)
    external_reference: Optional[str] = Field(None, max_length=100)
    remarks: Optional[str] = None
    items: Optional[List[GoodsReceiptItemCreate]] = None


class GoodsReceiptResponse(BaseModel):
    id: uuid.UUID
    receipt_number: str
    warehouse_id: uuid.UUID
    supplier_reference: Optional[str] = None
    external_reference: Optional[str] = None
    receipt_date: datetime
    status: str
    remarks: Optional[str] = None
    created_by: Optional[uuid.UUID] = None
    approved_by: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    warehouse_code: Optional[str] = None
    warehouse_name: Optional[str] = None
    items: List[GoodsReceiptItemResponse] = []

    model_config = ConfigDict(from_attributes=True)


class PaginatedGoodsReceiptResponse(BaseModel):
    items: List[GoodsReceiptResponse]
    total: int
    skip: int
    limit: int


# --- Goods Issue Schemas ---

class GoodsIssueItemCreate(BaseModel):
    product_id: uuid.UUID
    storage_location_id: Optional[uuid.UUID] = None
    quantity: Decimal = Field(..., gt=0, description="Quantity issued (must be positive)")
    unit_id: Optional[uuid.UUID] = None
    remarks: Optional[str] = None


class GoodsIssueItemResponse(BaseModel):
    id: uuid.UUID
    goods_issue_id: uuid.UUID
    product_id: uuid.UUID
    storage_location_id: Optional[uuid.UUID] = None
    quantity: Decimal
    unit_id: Optional[uuid.UUID] = None
    remarks: Optional[str] = None

    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    storage_location_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class GoodsIssueCreate(BaseModel):
    issue_number: str = Field(..., min_length=3, max_length=100)
    warehouse_id: uuid.UUID
    issue_date: Optional[datetime] = None
    issue_reason: str = Field(..., description="Consumption, Internal, Damage, Sample, Adjustment, Other")
    remarks: Optional[str] = None
    items: List[GoodsIssueItemCreate] = Field(..., min_length=1)



class GoodsIssueUpdate(BaseModel):
    issue_reason: Optional[str] = Field(None, description="Consumption, Internal, Damage, Sample, Adjustment, Other")
    remarks: Optional[str] = None
    items: Optional[List[GoodsIssueItemCreate]] = None


class GoodsIssueResponse(BaseModel):
    id: uuid.UUID
    issue_number: str
    warehouse_id: uuid.UUID
    issue_date: datetime
    issue_reason: str
    status: str
    remarks: Optional[str] = None
    created_by: Optional[uuid.UUID] = None
    approved_by: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    warehouse_code: Optional[str] = None
    warehouse_name: Optional[str] = None
    items: List[GoodsIssueItemResponse] = []

    model_config = ConfigDict(from_attributes=True)


class PaginatedGoodsIssueResponse(BaseModel):
    items: List[GoodsIssueResponse]
    total: int
    skip: int
    limit: int


# --- Stock Transfer Schemas ---

class StockTransferItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: Decimal = Field(..., gt=0, description="Quantity transferred (must be positive)")
    unit_id: Optional[uuid.UUID] = None
    remarks: Optional[str] = None


class StockTransferItemResponse(BaseModel):
    id: uuid.UUID
    transfer_id: uuid.UUID
    product_id: uuid.UUID
    quantity: Decimal
    unit_id: Optional[uuid.UUID] = None
    remarks: Optional[str] = None

    product_sku: Optional[str] = None
    product_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class StockTransferCreate(BaseModel):
    transfer_number: str = Field(..., min_length=3, max_length=100)
    source_warehouse_id: uuid.UUID
    destination_warehouse_id: uuid.UUID
    source_location_id: Optional[uuid.UUID] = None
    destination_location_id: Optional[uuid.UUID] = None
    transfer_date: Optional[datetime] = None
    remarks: Optional[str] = None
    items: List[StockTransferItemCreate] = Field(..., min_length=1)



class StockTransferUpdate(BaseModel):
    source_location_id: Optional[uuid.UUID] = None
    destination_location_id: Optional[uuid.UUID] = None
    remarks: Optional[str] = None
    items: Optional[List[StockTransferItemCreate]] = None


class StockTransferResponse(BaseModel):
    id: uuid.UUID
    transfer_number: str
    source_warehouse_id: uuid.UUID
    destination_warehouse_id: uuid.UUID
    source_location_id: Optional[uuid.UUID] = None
    destination_location_id: Optional[uuid.UUID] = None
    transfer_date: datetime
    status: str
    remarks: Optional[str] = None
    created_by: Optional[uuid.UUID] = None
    approved_by: Optional[uuid.UUID] = None
    completed_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    source_warehouse_code: Optional[str] = None
    destination_warehouse_code: Optional[str] = None
    source_location_code: Optional[str] = None
    destination_location_code: Optional[str] = None
    items: List[StockTransferItemResponse] = []

    model_config = ConfigDict(from_attributes=True)


class PaginatedStockTransferResponse(BaseModel):
    items: List[StockTransferResponse]
    total: int
    skip: int
    limit: int
