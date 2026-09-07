from datetime import datetime
from decimal import Decimal
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ----------------------------------------------------
# Customer Schemas
# ----------------------------------------------------
class CustomerCategoryBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    description: Optional[str] = None


class CustomerCategoryCreate(CustomerCategoryBase):
    pass


class CustomerCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class CustomerCategoryResponse(CustomerCategoryBase):
    id: uuid.UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CustomerContactBase(BaseModel):
    contact_person: str = Field(..., max_length=150)
    email: Optional[str] = None
    phone: Optional[str] = None
    designation: Optional[str] = None
    is_primary: bool = False


class CustomerContactCreate(CustomerContactBase):
    pass


class CustomerContactResponse(CustomerContactBase):
    id: uuid.UUID
    customer_id: uuid.UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CustomerAddressBase(BaseModel):
    address_type: str = Field("Billing", description="Billing, Shipping, Both")
    address_line1: str = Field(..., max_length=255)
    address_line2: Optional[str] = None
    city: str = Field(..., max_length=100)
    state: str = Field(..., max_length=100)
    postal_code: str = Field(..., max_length=20)
    country: str = Field("India", max_length=100)
    is_default: bool = False


class CustomerAddressCreate(CustomerAddressBase):
    pass


class CustomerAddressResponse(CustomerAddressBase):
    id: uuid.UUID
    customer_id: uuid.UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CustomerDocumentCreate(BaseModel):
    file_id: uuid.UUID
    document_type: str = Field(..., max_length=100)


class CustomerDocumentResponse(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    file_id: uuid.UUID
    document_type: str
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CustomerBase(BaseModel):
    customer_code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    category_id: Optional[uuid.UUID] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    tax_id: Optional[str] = None
    credit_limit: Decimal = Field(Decimal("0.00"), ge=0)
    credit_days: int = Field(30, ge=0)
    payment_terms: str = "Net 30"
    status: str = Field("Active", description="Active, Inactive, Blacklisted")
    is_preferred: bool = False
    rating: Decimal = Field(Decimal("5.00"), ge=0, le=5)
    notes: Optional[str] = None


class CustomerCreate(CustomerBase):
    contacts: Optional[List[CustomerContactCreate]] = None
    addresses: Optional[List[CustomerAddressCreate]] = None


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    tax_id: Optional[str] = None
    credit_limit: Optional[Decimal] = None
    credit_days: Optional[int] = None
    payment_terms: Optional[str] = None
    status: Optional[str] = None
    is_preferred: Optional[bool] = None
    rating: Optional[Decimal] = None
    notes: Optional[str] = None


class CustomerResponse(CustomerBase):
    id: uuid.UUID
    category: Optional[CustomerCategoryResponse] = None
    contacts: List[CustomerContactResponse] = []
    addresses: List[CustomerAddressResponse] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ----------------------------------------------------
# Pricing & Discount Schemas
# ----------------------------------------------------
class PriceListBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=150)
    currency: str = "INR"
    is_active: bool = True
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    description: Optional[str] = None


class PriceListCreate(PriceListBase):
    pass


class PriceListResponse(PriceListBase):
    id: uuid.UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PricingRuleBase(BaseModel):
    price_list_id: uuid.UUID
    product_id: uuid.UUID
    min_quantity: Decimal = Field(Decimal("1.0000"), gt=0)
    unit_price: Decimal = Field(..., ge=0)
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None


class PricingRuleCreate(PricingRuleBase):
    pass


class PricingRuleResponse(PricingRuleBase):
    id: uuid.UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DiscountRuleBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=150)
    discount_type: str = Field("Line", description="Line or Document")
    calculation_type: str = Field("Percentage", description="Percentage or FixedAmount")
    discount_value: Decimal = Field(..., ge=0)
    min_order_value: Decimal = Field(Decimal("0.0000"), ge=0)
    min_quantity: Decimal = Field(Decimal("0.0000"), ge=0)
    is_active: bool = True
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None


class DiscountRuleCreate(DiscountRuleBase):
    pass


class DiscountRuleResponse(DiscountRuleBase):
    id: uuid.UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ----------------------------------------------------
# Sales Quotation Schemas
# ----------------------------------------------------
class SalesQuotationItemCreate(BaseModel):
    product_id: uuid.UUID
    description: Optional[str] = None
    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    discount_type: str = "Percentage"
    discount_value: Decimal = Decimal("0.0000")
    tax_rate: Decimal = Decimal("0.00")
    warehouse_id: Optional[uuid.UUID] = None


class SalesQuotationItemResponse(BaseModel):
    id: uuid.UUID
    quotation_id: uuid.UUID
    product_id: uuid.UUID
    description: Optional[str] = None
    quantity: Decimal
    unit_price: Decimal
    discount_type: str
    discount_value: Decimal
    discount_amount: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    line_total: Decimal
    warehouse_id: Optional[uuid.UUID] = None

    model_config = ConfigDict(from_attributes=True)


class SalesQuotationCreate(BaseModel):
    customer_id: uuid.UUID
    validity_date: Optional[datetime] = None
    currency: str = "INR"
    remarks: Optional[str] = None
    items: List[SalesQuotationItemCreate]


class SalesQuotationUpdate(BaseModel):
    validity_date: Optional[datetime] = None
    currency: Optional[str] = None
    remarks: Optional[str] = None
    items: Optional[List[SalesQuotationItemCreate]] = None


class SalesQuotationResponse(BaseModel):
    id: uuid.UUID
    quotation_number: str
    customer_id: uuid.UUID
    customer: Optional[CustomerResponse] = None
    quotation_date: datetime
    validity_date: Optional[datetime] = None
    currency: str
    status: str
    revision_number: int
    subtotal_amount: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    remarks: Optional[str] = None
    created_by: Optional[uuid.UUID] = None
    approved_by: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None
    items: List[SalesQuotationItemResponse] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ----------------------------------------------------
# Sales Order Schemas
# ----------------------------------------------------
class SalesOrderItemCreate(BaseModel):
    product_id: uuid.UUID
    description: Optional[str] = None
    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    discount_type: str = "Percentage"
    discount_value: Decimal = Decimal("0.0000")
    tax_rate: Decimal = Decimal("0.00")
    warehouse_id: Optional[uuid.UUID] = None
    delivery_date: Optional[datetime] = None


class SalesOrderItemResponse(BaseModel):
    id: uuid.UUID
    sales_order_id: uuid.UUID
    product_id: uuid.UUID
    description: Optional[str] = None
    quantity: Decimal
    delivered_quantity: Decimal
    unit_price: Decimal
    discount_type: str
    discount_value: Decimal
    discount_amount: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    line_total: Decimal
    warehouse_id: Optional[uuid.UUID] = None
    delivery_date: Optional[datetime] = None
    status: str

    model_config = ConfigDict(from_attributes=True)


class SalesOrderCreate(BaseModel):
    customer_id: uuid.UUID
    quotation_id: Optional[uuid.UUID] = None
    currency: str = "INR"
    payment_terms: str = "Net 30"
    shipping_address_id: Optional[uuid.UUID] = None
    billing_address_id: Optional[uuid.UUID] = None
    remarks: Optional[str] = None
    items: List[SalesOrderItemCreate]


class SalesOrderUpdate(BaseModel):
    payment_terms: Optional[str] = None
    shipping_address_id: Optional[uuid.UUID] = None
    billing_address_id: Optional[uuid.UUID] = None
    remarks: Optional[str] = None
    items: Optional[List[SalesOrderItemCreate]] = None


class SalesOrderResponse(BaseModel):
    id: uuid.UUID
    order_number: str
    customer_id: uuid.UUID
    customer: Optional[CustomerResponse] = None
    quotation_id: Optional[uuid.UUID] = None
    order_date: datetime
    status: str
    delivery_status: str
    revision_number: int
    currency: str
    subtotal_amount: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    payment_terms: str
    shipping_address_id: Optional[uuid.UUID] = None
    billing_address_id: Optional[uuid.UUID] = None
    remarks: Optional[str] = None
    created_by: Optional[uuid.UUID] = None
    approved_by: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None
    items: List[SalesOrderItemResponse] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ----------------------------------------------------
# Delivery Order Schemas
# ----------------------------------------------------
class DeliveryOrderItemCreate(BaseModel):
    sales_order_item_id: uuid.UUID
    product_id: uuid.UUID
    quantity: Decimal = Field(..., gt=0)


class DeliveryOrderItemResponse(BaseModel):
    id: uuid.UUID
    delivery_order_id: uuid.UUID
    sales_order_item_id: uuid.UUID
    product_id: uuid.UUID
    quantity: Decimal

    model_config = ConfigDict(from_attributes=True)


class DeliveryOrderCreate(BaseModel):
    sales_order_id: uuid.UUID
    warehouse_id: uuid.UUID
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    delivery_notes: Optional[str] = None
    items: List[DeliveryOrderItemCreate]


class DeliveryOrderResponse(BaseModel):
    id: uuid.UUID
    delivery_number: str
    sales_order_id: uuid.UUID
    warehouse_id: uuid.UUID
    goods_issue_id: Optional[uuid.UUID] = None
    dispatch_date: datetime
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    status: str
    delivery_notes: Optional[str] = None
    created_by: Optional[uuid.UUID] = None
    items: List[DeliveryOrderItemResponse] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ----------------------------------------------------
# Sales Return Schemas
# ----------------------------------------------------
class SalesReturnItemCreate(BaseModel):
    sales_order_item_id: uuid.UUID
    product_id: uuid.UUID
    quantity: Decimal = Field(..., gt=0)
    reason: Optional[str] = None


class SalesReturnItemResponse(BaseModel):
    id: uuid.UUID
    sales_return_id: uuid.UUID
    sales_order_item_id: uuid.UUID
    product_id: uuid.UUID
    quantity: Decimal
    unit_price: Decimal
    refund_amount: Decimal
    reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SalesReturnCreate(BaseModel):
    sales_order_id: uuid.UUID
    delivery_order_id: Optional[uuid.UUID] = None
    warehouse_id: uuid.UUID
    reason_code: str = Field(..., description="Damaged, Defective, WrongItem, CustomerCancellation, ExcessShipment, Other")
    remarks: Optional[str] = None
    items: List[SalesReturnItemCreate]


class SalesReturnResponse(BaseModel):
    id: uuid.UUID
    return_number: str
    sales_order_id: uuid.UUID
    delivery_order_id: Optional[uuid.UUID] = None
    customer_id: uuid.UUID
    warehouse_id: uuid.UUID
    goods_receipt_id: Optional[uuid.UUID] = None
    return_date: datetime
    status: str
    reason_code: str
    total_refund_amount: Decimal
    remarks: Optional[str] = None
    created_by: Optional[uuid.UUID] = None
    approved_by: Optional[uuid.UUID] = None
    items: List[SalesReturnItemResponse] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ----------------------------------------------------
# Invoice Payload Schema (For Future Finance Domain)
# ----------------------------------------------------
class SalesInvoicePayloadItem(BaseModel):
    product_id: uuid.UUID
    product_sku: str
    product_name: str
    quantity: Decimal
    unit_price: Decimal
    discount_amount: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    line_total: Decimal


class SalesInvoicePayload(BaseModel):
    sales_order_id: uuid.UUID
    order_number: str
    customer_id: uuid.UUID
    customer_name: str
    customer_tax_id: Optional[str] = None
    currency: str
    order_date: datetime
    subtotal_amount: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    payment_terms: str
    items: List[SalesInvoicePayloadItem]
    generated_at: datetime


# ----------------------------------------------------
# Analytics & Reports Schemas
# ----------------------------------------------------
class SalesAnalyticsResponse(BaseModel):
    total_revenue: Decimal
    total_orders: int
    avg_order_value: Decimal
    total_customers: int
    top_customers: List[Dict[str, Any]]
    top_products: List[Dict[str, Any]]
    monthly_sales: List[Dict[str, Any]]
    warehouse_sales: List[Dict[str, Any]]


class CustomerLedgerEntry(BaseModel):
    date: datetime
    document_number: str
    document_type: str
    amount: Decimal
    balance: Decimal
    notes: Optional[str] = None


# ----------------------------------------------------
# Global Search Schema
# ----------------------------------------------------
class SalesSearchResult(BaseModel):
    entity_type: str
    entity_id: str
    title: str
    subtitle: Optional[str] = None
    status: Optional[str] = None
    details: Dict[str, Any] = {}
