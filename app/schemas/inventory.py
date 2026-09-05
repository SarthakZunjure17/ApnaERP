from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, model_validator


# --- Enums ---

class ProductTypeEnum(str, Enum):
    INVENTORY = "Inventory"
    SERVICE = "Service"
    CONSUMABLE = "Consumable"
    DIGITAL = "Digital"
    ASSET = "Asset"
    GOODS = "Goods"
    NON_STOCK = "Non-Stock"


class ProductStatusEnum(str, Enum):
    DRAFT = "Draft"
    ACTIVE = "Active"
    DISCONTINUED = "Discontinued"
    ARCHIVED = "Archived"


class WarehouseTypeEnum(str, Enum):
    MAIN = "MAIN"
    DISTRIBUTION = "DISTRIBUTION"
    RETAIL = "RETAIL"
    VIRTUAL = "VIRTUAL"
    TRANSIT = "TRANSIT"


class StorageLocationTypeEnum(str, Enum):
    STORAGE = "Storage"
    RECEIVING = "Receiving"
    SHIPPING = "Shipping"
    QUARANTINE = "Quarantine"
    RETURNS = "Returns"
    DAMAGED = "Damaged"
    SHELF = "Shelf"
    RACK = "Rack"
    BIN = "Bin"
    FLOOR = "Floor"
    COLD_STORAGE = "Cold Storage"
    DISPATCH = "Dispatch"


class ValuationMethodEnum(str, Enum):
    FIFO = "FIFO"
    LIFO = "LIFO"
    WEIGHTED_AVERAGE = "WEIGHTED_AVERAGE"
    STANDARD = "STANDARD"


class CostingMethodEnum(str, Enum):
    STANDARD = "STANDARD"
    ACTUAL = "ACTUAL"
    MOVING_AVERAGE = "MOVING_AVERAGE"


class ReorderStrategyEnum(str, Enum):
    MIN_MAX = "MIN_MAX"
    FIXED_ORDER_QTY = "FIXED_ORDER_QTY"
    PERIODIC = "PERIODIC"


class ReservationBehaviorEnum(str, Enum):
    STRICT = "STRICT"
    SOFT = "SOFT"
    MANUAL = "MANUAL"


class AttributeDataTypeEnum(str, Enum):
    TEXT = "Text"
    NUMBER = "Number"
    BOOLEAN = "Boolean"
    DATE = "Date"
    LIST = "List"


class DocumentTypeEnum(str, Enum):
    MANUAL = "Manual"
    WARRANTY = "Warranty"
    SPECIFICATION = "Specification"
    COMPLIANCE = "Compliance"
    CERTIFICATE = "Certificate"
    IMAGE = "Image"


# --- ProductCategory Schemas ---

class ProductCategoryBase(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    parent_id: Optional[uuid.UUID] = None
    is_active: bool = True


class ProductCategoryCreate(ProductCategoryBase):
    pass


class ProductCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    code: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    parent_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None


class ProductCategoryResponse(ProductCategoryBase):
    id: uuid.UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProductCategoryTreeResponse(ProductCategoryResponse):
    children: List["ProductCategoryTreeResponse"] = []


# --- UnitOfMeasure Schemas ---

class UnitOfMeasureBase(BaseModel):
    name: str = Field(..., max_length=100)
    symbol: str = Field(..., max_length=20)
    code: Optional[str] = Field(None, max_length=50)
    category: str = Field("Count", max_length=50)
    precision: int = Field(2, ge=0, le=6)
    base_unit: Optional[str] = Field(None, max_length=20)
    is_active: bool = True

    @model_validator(mode="before")
    @classmethod
    def set_defaults_and_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("code") and data.get("symbol"):
                data["code"] = str(data["symbol"]).upper()
            if "uom_type" in data and not data.get("category"):
                data["category"] = data["uom_type"]
            if "decimal_precision" in data and "precision" not in data:
                data["precision"] = data["decimal_precision"]
        return data


class UnitOfMeasureCreate(UnitOfMeasureBase):
    pass


class UnitOfMeasureUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    symbol: Optional[str] = Field(None, max_length=20)
    code: Optional[str] = Field(None, max_length=50)
    category: Optional[str] = Field(None, max_length=50)
    precision: Optional[int] = Field(None, ge=0, le=6)
    base_unit: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None

    @model_validator(mode="before")
    @classmethod
    def set_update_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "uom_type" in data and not data.get("category"):
                data["category"] = data["uom_type"]
            if "decimal_precision" in data and "precision" not in data:
                data["precision"] = data["decimal_precision"]
        return data


class UnitOfMeasureResponse(UnitOfMeasureBase):
    id: uuid.UUID
    uom_type: Optional[str] = None
    decimal_precision: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# --- Brand Schemas ---

class BrandBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    is_active: bool = True


class BrandCreate(BrandBase):
    pass


class BrandUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class BrandResponse(BrandBase):
    id: uuid.UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# --- Warehouse Schemas ---

class WarehouseBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    warehouse_type: WarehouseTypeEnum = WarehouseTypeEnum.MAIN
    address: Optional[str] = Field(None, max_length=255)
    address_line_1: Optional[str] = Field(None, max_length=255)
    address_line_2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    timezone: str = Field("UTC", max_length=50)
    manager_employee_id: Optional[uuid.UUID] = None
    contact_person: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=30)
    email: Optional[str] = Field(None, max_length=100)
    is_active: bool = True


class WarehouseCreate(WarehouseBase):
    pass


class WarehouseUpdate(BaseModel):
    code: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    warehouse_type: Optional[WarehouseTypeEnum] = None
    address: Optional[str] = Field(None, max_length=255)
    address_line_1: Optional[str] = Field(None, max_length=255)
    address_line_2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    timezone: Optional[str] = Field(None, max_length=50)
    manager_employee_id: Optional[uuid.UUID] = None
    contact_person: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=30)
    email: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


class WarehouseResponse(WarehouseBase):
    id: uuid.UUID
    manager_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# --- StorageLocation Schemas ---

class StorageLocationBase(BaseModel):
    warehouse_id: uuid.UUID
    parent_id: Optional[uuid.UUID] = None
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    location_type: StorageLocationTypeEnum = StorageLocationTypeEnum.BIN
    is_active: bool = True

    @model_validator(mode="before")
    @classmethod
    def set_location_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "parent_location_id" in data and not data.get("parent_id"):
                data["parent_id"] = data["parent_location_id"]
        return data


class StorageLocationCreate(StorageLocationBase):
    pass


class StorageLocationUpdate(BaseModel):
    warehouse_id: Optional[uuid.UUID] = None
    parent_id: Optional[uuid.UUID] = None
    code: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    location_type: Optional[StorageLocationTypeEnum] = None
    is_active: Optional[bool] = None

    @model_validator(mode="before")
    @classmethod
    def set_location_update_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "parent_location_id" in data and not data.get("parent_id"):
                data["parent_id"] = data["parent_location_id"]
        return data


class StorageLocationResponse(StorageLocationBase):
    id: uuid.UUID
    parent_location_id: Optional[uuid.UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class StorageLocationTreeResponse(StorageLocationResponse):
    children: List["StorageLocationTreeResponse"] = []


# --- Product-Warehouse Configuration Schemas ---

class ProductWarehouseBase(BaseModel):
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    preferred_location_id: Optional[uuid.UUID] = None
    reorder_level: Optional[Decimal] = Field(None, ge=0)
    reorder_quantity: Optional[Decimal] = Field(None, ge=0)
    minimum_stock: Optional[Decimal] = Field(None, ge=0)
    maximum_stock: Optional[Decimal] = Field(None, ge=0)
    safety_stock: Optional[Decimal] = Field(None, ge=0)
    is_active: bool = True

    @model_validator(mode="after")
    def validate_thresholds(self):
        if self.minimum_stock is not None and self.maximum_stock is not None:
            if self.minimum_stock > self.maximum_stock:
                raise ValueError("minimum_stock cannot be greater than maximum_stock")
        return self


class ProductWarehouseCreate(ProductWarehouseBase):
    pass


class ProductWarehouseUpdate(BaseModel):
    preferred_location_id: Optional[uuid.UUID] = None
    reorder_level: Optional[Decimal] = Field(None, ge=0)
    reorder_quantity: Optional[Decimal] = Field(None, ge=0)
    minimum_stock: Optional[Decimal] = Field(None, ge=0)
    maximum_stock: Optional[Decimal] = Field(None, ge=0)
    safety_stock: Optional[Decimal] = Field(None, ge=0)
    is_active: Optional[bool] = None

    @model_validator(mode="after")
    def validate_update_thresholds(self):
        if self.minimum_stock is not None and self.maximum_stock is not None:
            if self.minimum_stock > self.maximum_stock:
                raise ValueError("minimum_stock cannot be greater than maximum_stock")
        return self


class ProductWarehouseResponse(ProductWarehouseBase):
    id: uuid.UUID
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    warehouse_code: Optional[str] = None
    warehouse_name: Optional[str] = None
    preferred_location_code: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# --- Inventory Policy Schemas ---

class InventoryPolicyBase(BaseModel):
    warehouse_id: Optional[uuid.UUID] = None
    valuation_method: ValuationMethodEnum = ValuationMethodEnum.FIFO
    costing_method: CostingMethodEnum = CostingMethodEnum.STANDARD
    negative_stock_allowed: bool = False
    default_reorder_strategy: ReorderStrategyEnum = ReorderStrategyEnum.MIN_MAX
    default_reservation_behavior: ReservationBehaviorEnum = ReservationBehaviorEnum.STRICT
    low_stock_alert_enabled: bool = True
    is_active: bool = True


class InventoryPolicyCreate(InventoryPolicyBase):
    pass


class InventoryPolicyUpdate(BaseModel):
    valuation_method: Optional[ValuationMethodEnum] = None
    costing_method: Optional[CostingMethodEnum] = None
    negative_stock_allowed: Optional[bool] = None
    default_reorder_strategy: Optional[ReorderStrategyEnum] = None
    default_reservation_behavior: Optional[ReservationBehaviorEnum] = None
    low_stock_alert_enabled: Optional[bool] = None
    is_active: Optional[bool] = None


class InventoryPolicyResponse(InventoryPolicyBase):
    id: uuid.UUID
    warehouse_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# --- ProductAttribute Schemas ---

class ProductAttributeBase(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=50)
    data_type: AttributeDataTypeEnum = AttributeDataTypeEnum.TEXT


class ProductAttributeCreate(ProductAttributeBase):
    pass


class ProductAttributeUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    code: Optional[str] = Field(None, max_length=50)
    data_type: Optional[AttributeDataTypeEnum] = None


class ProductAttributeResponse(ProductAttributeBase):
    id: uuid.UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProductAttributeValueCreate(BaseModel):
    attribute_id: uuid.UUID
    value: str = Field(..., max_length=500)


class ProductAttributeValueResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    attribute_id: uuid.UUID
    value: str
    attribute_code: Optional[str] = None
    attribute_name: Optional[str] = None
    data_type: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# --- ProductDocument Schemas ---

class ProductDocumentCreate(BaseModel):
    file_id: uuid.UUID
    document_type: DocumentTypeEnum = DocumentTypeEnum.SPECIFICATION


class ProductDocumentResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    file_id: uuid.UUID
    document_type: DocumentTypeEnum
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# --- Product Schemas ---

class ProductBase(BaseModel):
    sku: str = Field(..., max_length=100)
    barcode: Optional[str] = Field(None, max_length=100)
    name: str = Field(..., max_length=150)
    description: Optional[str] = Field(None, max_length=500)
    model_number: Optional[str] = Field(None, max_length=100)
    category_id: uuid.UUID
    brand_id: Optional[uuid.UUID] = None
    base_unit_id: uuid.UUID
    purchase_unit_id: Optional[uuid.UUID] = None
    sales_unit_id: Optional[uuid.UUID] = None
    product_type: ProductTypeEnum = ProductTypeEnum.INVENTORY
    is_active: bool = True
    is_stockable: bool = True
    is_sellable: bool = True
    is_purchasable: bool = True
    track_inventory: bool = True
    allow_negative_stock: bool = False
    default_warehouse_id: Optional[uuid.UUID] = None
    reorder_level: Optional[Decimal] = Field(None, ge=0)
    reorder_quantity: Optional[Decimal] = Field(None, ge=0)
    minimum_stock: Optional[Decimal] = Field(None, ge=0)
    maximum_stock: Optional[Decimal] = Field(None, ge=0)
    lead_time_days: int = Field(0, ge=0)
    default_unit_price: Optional[Decimal] = Field(None, ge=0)
    weight: Optional[float] = Field(None, ge=0)
    height: Optional[float] = Field(None, ge=0)
    width: Optional[float] = Field(None, ge=0)
    length: Optional[float] = Field(None, ge=0)
    volume: Optional[float] = Field(None, ge=0)
    image_file_id: Optional[uuid.UUID] = None
    metadata_json: Optional[Dict[str, Any]] = None
    status: ProductStatusEnum = ProductStatusEnum.DRAFT

    @model_validator(mode="before")
    @classmethod
    def set_product_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "base_uom_id" in data and "base_unit_id" not in data:
                data["base_unit_id"] = data["base_uom_id"]
            if "is_stockable" in data and "track_inventory" not in data:
                data["track_inventory"] = data["is_stockable"]
            elif "track_inventory" in data and "is_stockable" not in data:
                data["is_stockable"] = data["track_inventory"]
            if "metadata" in data and "metadata_json" not in data:
                data["metadata_json"] = data["metadata"]
        return data

    @model_validator(mode="after")
    def validate_stock_thresholds(self):
        if self.minimum_stock is not None and self.maximum_stock is not None:
            if self.minimum_stock > self.maximum_stock:
                raise ValueError("minimum_stock cannot be greater than maximum_stock")
        return self


class ProductCreate(ProductBase):
    attributes: Optional[List[ProductAttributeValueCreate]] = None


class ProductUpdate(BaseModel):
    sku: Optional[str] = Field(None, max_length=100)
    barcode: Optional[str] = Field(None, max_length=100)
    name: Optional[str] = Field(None, max_length=150)
    description: Optional[str] = Field(None, max_length=500)
    model_number: Optional[str] = Field(None, max_length=100)
    category_id: Optional[uuid.UUID] = None
    brand_id: Optional[uuid.UUID] = None
    base_unit_id: Optional[uuid.UUID] = None
    purchase_unit_id: Optional[uuid.UUID] = None
    sales_unit_id: Optional[uuid.UUID] = None
    product_type: Optional[ProductTypeEnum] = None
    is_active: Optional[bool] = None
    is_stockable: Optional[bool] = None
    is_sellable: Optional[bool] = None
    is_purchasable: Optional[bool] = None
    track_inventory: Optional[bool] = None
    allow_negative_stock: Optional[bool] = None
    default_warehouse_id: Optional[uuid.UUID] = None
    reorder_level: Optional[Decimal] = Field(None, ge=0)
    reorder_quantity: Optional[Decimal] = Field(None, ge=0)
    minimum_stock: Optional[Decimal] = Field(None, ge=0)
    maximum_stock: Optional[Decimal] = Field(None, ge=0)
    lead_time_days: Optional[int] = Field(None, ge=0)
    default_unit_price: Optional[Decimal] = Field(None, ge=0)
    weight: Optional[float] = Field(None, ge=0)
    height: Optional[float] = Field(None, ge=0)
    width: Optional[float] = Field(None, ge=0)
    length: Optional[float] = Field(None, ge=0)
    volume: Optional[float] = Field(None, ge=0)
    image_file_id: Optional[uuid.UUID] = None
    metadata_json: Optional[Dict[str, Any]] = None
    status: Optional[ProductStatusEnum] = None

    @model_validator(mode="before")
    @classmethod
    def set_product_update_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "base_uom_id" in data and "base_unit_id" not in data:
                data["base_unit_id"] = data["base_uom_id"]
            if "is_stockable" in data and "track_inventory" not in data:
                data["track_inventory"] = data["is_stockable"]
            elif "track_inventory" in data and "is_stockable" not in data:
                data["is_stockable"] = data["track_inventory"]
            if "metadata" in data and "metadata_json" not in data:
                data["metadata_json"] = data["metadata"]
        return data

    @model_validator(mode="after")
    def validate_stock_thresholds_update(self):
        if self.minimum_stock is not None and self.maximum_stock is not None:
            if self.minimum_stock > self.maximum_stock:
                raise ValueError("minimum_stock cannot be greater than maximum_stock")
        return self


class ProductResponse(ProductBase):
    id: uuid.UUID
    base_uom_id: Optional[uuid.UUID] = None
    category_name: Optional[str] = None
    brand_name: Optional[str] = None
    base_unit_name: Optional[str] = None
    default_warehouse_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProductDetailResponse(ProductResponse):
    attributes: List[ProductAttributeValueResponse] = []
    documents: List[ProductDocumentResponse] = []
    warehouse_configs: List[ProductWarehouseResponse] = []
