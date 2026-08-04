from datetime import datetime
from enum import Enum
from typing import Any, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


# --- Enums ---

class ProductTypeEnum(str, Enum):
    INVENTORY = "Inventory"
    SERVICE = "Service"
    CONSUMABLE = "Consumable"
    DIGITAL = "Digital"
    ASSET = "Asset"


class ProductStatusEnum(str, Enum):
    DRAFT = "Draft"
    ACTIVE = "Active"
    DISCONTINUED = "Discontinued"
    ARCHIVED = "Archived"


class StorageLocationTypeEnum(str, Enum):
    SHELF = "Shelf"
    RACK = "Rack"
    BIN = "Bin"
    FLOOR = "Floor"
    COLD_STORAGE = "Cold Storage"
    QUARANTINE = "Quarantine"
    RECEIVING = "Receiving"
    DISPATCH = "Dispatch"


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
    category: str = Field(..., max_length=50)
    precision: int = Field(2, ge=0, le=6)
    base_unit: Optional[str] = Field(None, max_length=20)
    is_active: bool = True


class UnitOfMeasureCreate(UnitOfMeasureBase):
    pass


class UnitOfMeasureUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    symbol: Optional[str] = Field(None, max_length=20)
    category: Optional[str] = Field(None, max_length=50)
    precision: Optional[int] = Field(None, ge=0, le=6)
    base_unit: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None


class UnitOfMeasureResponse(UnitOfMeasureBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

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
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Warehouse Schemas ---

class WarehouseBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    address: Optional[str] = Field(None, max_length=255)
    contact_person: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=30)
    email: Optional[str] = Field(None, max_length=100)
    is_active: bool = True


class WarehouseCreate(WarehouseBase):
    pass


class WarehouseUpdate(BaseModel):
    code: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=255)
    contact_person: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=30)
    email: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


class WarehouseResponse(WarehouseBase):
    id: uuid.UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# --- StorageLocation Schemas ---

class StorageLocationBase(BaseModel):
    warehouse_id: uuid.UUID
    parent_id: Optional[uuid.UUID] = None
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    location_type: StorageLocationTypeEnum = StorageLocationTypeEnum.BIN
    is_active: bool = True


class StorageLocationCreate(StorageLocationBase):
    pass


class StorageLocationUpdate(BaseModel):
    warehouse_id: Optional[uuid.UUID] = None
    parent_id: Optional[uuid.UUID] = None
    code: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, max_length=100)
    location_type: Optional[StorageLocationTypeEnum] = None
    is_active: Optional[bool] = None


class StorageLocationResponse(StorageLocationBase):
    id: uuid.UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class StorageLocationTreeResponse(StorageLocationResponse):
    children: List["StorageLocationTreeResponse"] = []


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
    created_at: datetime
    updated_at: datetime

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
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Product Schemas ---

class ProductBase(BaseModel):
    sku: str = Field(..., max_length=100)
    barcode: Optional[str] = Field(None, max_length=100)
    name: str = Field(..., max_length=150)
    description: Optional[str] = Field(None, max_length=500)
    category_id: uuid.UUID
    brand_id: Optional[uuid.UUID] = None
    base_unit_id: uuid.UUID
    purchase_unit_id: Optional[uuid.UUID] = None
    sales_unit_id: Optional[uuid.UUID] = None
    product_type: ProductTypeEnum = ProductTypeEnum.INVENTORY
    track_inventory: bool = True
    allow_negative_stock: bool = False
    default_warehouse_id: Optional[uuid.UUID] = None
    weight: Optional[float] = Field(None, ge=0)
    height: Optional[float] = Field(None, ge=0)
    width: Optional[float] = Field(None, ge=0)
    length: Optional[float] = Field(None, ge=0)
    volume: Optional[float] = Field(None, ge=0)
    image_file_id: Optional[uuid.UUID] = None
    status: ProductStatusEnum = ProductStatusEnum.DRAFT


class ProductCreate(ProductBase):
    attributes: Optional[List[ProductAttributeValueCreate]] = None


class ProductUpdate(BaseModel):
    sku: Optional[str] = Field(None, max_length=100)
    barcode: Optional[str] = Field(None, max_length=100)
    name: Optional[str] = Field(None, max_length=150)
    description: Optional[str] = Field(None, max_length=500)
    category_id: Optional[uuid.UUID] = None
    brand_id: Optional[uuid.UUID] = None
    base_unit_id: Optional[uuid.UUID] = None
    purchase_unit_id: Optional[uuid.UUID] = None
    sales_unit_id: Optional[uuid.UUID] = None
    product_type: Optional[ProductTypeEnum] = None
    track_inventory: Optional[bool] = None
    allow_negative_stock: Optional[bool] = None
    default_warehouse_id: Optional[uuid.UUID] = None
    weight: Optional[float] = Field(None, ge=0)
    height: Optional[float] = Field(None, ge=0)
    width: Optional[float] = Field(None, ge=0)
    length: Optional[float] = Field(None, ge=0)
    volume: Optional[float] = Field(None, ge=0)
    image_file_id: Optional[uuid.UUID] = None
    status: Optional[ProductStatusEnum] = None


class ProductResponse(ProductBase):
    id: uuid.UUID
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
