from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


# --- Supplier Category ---
class SupplierCategoryCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None


class SupplierCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None


class SupplierCategoryResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedSupplierCategoryResponse(BaseModel):
    items: List[SupplierCategoryResponse]
    total: int
    page: int
    size: int
    pages: int


# --- Supplier Contacts ---
class SupplierContactCreate(BaseModel):
    contact_name: str = Field(..., min_length=2, max_length=100)
    designation: Optional[str] = None
    email: str = Field(..., min_length=5, max_length=150)
    phone: Optional[str] = None
    is_primary: bool = False


class SupplierContactUpdate(BaseModel):
    contact_name: Optional[str] = Field(None, min_length=2, max_length=100)
    designation: Optional[str] = None
    email: Optional[str] = Field(None, min_length=5, max_length=150)
    phone: Optional[str] = None
    is_primary: Optional[bool] = None


class SupplierContactResponse(BaseModel):
    id: uuid.UUID
    supplier_id: uuid.UUID
    contact_name: str
    designation: Optional[str] = None
    email: str
    phone: Optional[str] = None
    is_primary: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedSupplierContactResponse(BaseModel):
    items: List[SupplierContactResponse]
    total: int
    page: int
    size: int
    pages: int


# --- Supplier Addresses ---
class SupplierAddressCreate(BaseModel):
    address_type: str = Field("Billing", description="Billing, Shipping, Head Office, Branch")
    address_line1: str = Field(..., min_length=2, max_length=255)
    address_line2: Optional[str] = None
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=100)
    country: str = Field(..., min_length=2, max_length=100)
    postal_code: str = Field(..., min_length=2, max_length=20)
    is_primary: bool = False


class SupplierAddressUpdate(BaseModel):
    address_type: Optional[str] = Field(None, description="Billing, Shipping, Head Office, Branch")
    address_line1: Optional[str] = Field(None, min_length=2, max_length=255)
    address_line2: Optional[str] = None
    city: Optional[str] = Field(None, min_length=2, max_length=100)
    state: Optional[str] = Field(None, min_length=2, max_length=100)
    country: Optional[str] = Field(None, min_length=2, max_length=100)
    postal_code: Optional[str] = Field(None, min_length=2, max_length=20)
    is_primary: Optional[bool] = None


class SupplierAddressResponse(BaseModel):
    id: uuid.UUID
    supplier_id: uuid.UUID
    address_type: str
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    country: str
    postal_code: str
    is_primary: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedSupplierAddressResponse(BaseModel):
    items: List[SupplierAddressResponse]
    total: int
    page: int
    size: int
    pages: int


# --- Supplier Documents ---
class SupplierDocumentCreate(BaseModel):
    file_id: uuid.UUID
    document_type: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None


class SupplierDocumentUpdate(BaseModel):
    document_type: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None


class SupplierDocumentResponse(BaseModel):
    id: uuid.UUID
    supplier_id: uuid.UUID
    file_id: uuid.UUID
    document_type: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedSupplierDocumentResponse(BaseModel):
    items: List[SupplierDocumentResponse]
    total: int
    page: int
    size: int
    pages: int


# --- Supplier Ratings ---
class SupplierRatingCreate(BaseModel):
    score: Decimal = Field(..., ge=Decimal("1.0"), le=Decimal("5.0"))
    comments: Optional[str] = None


class SupplierRatingResponse(BaseModel):
    id: uuid.UUID
    supplier_id: uuid.UUID
    reviewer_id: uuid.UUID
    score: Decimal
    review_date: datetime
    comments: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedSupplierRatingResponse(BaseModel):
    items: List[SupplierRatingResponse]
    total: int
    page: int
    size: int
    pages: int


# --- Supplier Master ---
class SupplierCreate(BaseModel):
    code: Optional[str] = Field(None, min_length=2, max_length=50)
    name: str = Field(..., min_length=2, max_length=150)
    category_id: Optional[uuid.UUID] = None
    gst_vat_number: Optional[str] = None
    tax_id: Optional[str] = None
    payment_terms: str = "Net 30"
    credit_limit: Decimal = Field(Decimal("0.0"), ge=Decimal("0.0"))
    currency: str = "USD"
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc_swift: Optional[str] = None
    is_preferred: bool = False
    notes: Optional[str] = None
    contacts: Optional[List[SupplierContactCreate]] = None
    addresses: Optional[List[SupplierAddressCreate]] = None


class SupplierUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    category_id: Optional[uuid.UUID] = None
    gst_vat_number: Optional[str] = None
    tax_id: Optional[str] = None
    payment_terms: Optional[str] = None
    credit_limit: Optional[Decimal] = Field(None, ge=Decimal("0.0"))
    currency: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc_swift: Optional[str] = None
    status: Optional[str] = Field(None, description="Active, Inactive, Blacklisted")
    is_preferred: Optional[bool] = None
    notes: Optional[str] = None


class SupplierResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    category_id: Optional[uuid.UUID] = None
    gst_vat_number: Optional[str] = None
    tax_id: Optional[str] = None
    payment_terms: str
    credit_limit: Decimal
    currency: str
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc_swift: Optional[str] = None
    status: str
    is_preferred: bool
    rating: Decimal
    ontime_delivery_rate: Decimal
    quality_rating: Decimal
    total_spend: Decimal
    notes: Optional[str] = None
    contacts: List[SupplierContactResponse] = []
    addresses: List[SupplierAddressResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedSupplierResponse(BaseModel):
    items: List[SupplierResponse]
    total: int
    page: int
    size: int
    pages: int


# --- Purchase Requisition ---
class PurchaseRequisitionItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: Decimal = Field(..., gt=0)
    estimated_unit_price: Decimal = Field(Decimal("0.0"), ge=0)
    required_date: Optional[datetime] = None


class PurchaseRequisitionItemResponse(BaseModel):
    id: uuid.UUID
    requisition_id: uuid.UUID
    product_id: uuid.UUID
    quantity: Decimal
    fulfilled_quantity: Decimal
    estimated_unit_price: Decimal
    required_date: Optional[datetime] = None
    status: str
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PurchaseRequisitionCreate(BaseModel):
    department_id: Optional[uuid.UUID] = None
    required_date: datetime
    priority: str = Field("Medium", description="Low, Medium, High, Urgent")
    remarks: Optional[str] = None
    items: List[PurchaseRequisitionItemCreate]


class PurchaseRequisitionUpdate(BaseModel):
    department_id: Optional[uuid.UUID] = None
    required_date: Optional[datetime] = None
    priority: Optional[str] = None
    remarks: Optional[str] = None


class PurchaseRequisitionResponse(BaseModel):
    id: uuid.UUID
    requisition_number: str
    requester_id: uuid.UUID
    department_id: Optional[uuid.UUID] = None
    required_date: datetime
    priority: str
    status: str
    total_estimated_amount: Decimal
    remarks: Optional[str] = None
    items: List[PurchaseRequisitionItemResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedPurchaseRequisitionResponse(BaseModel):
    items: List[PurchaseRequisitionResponse]
    total: int
    page: int
    size: int
    pages: int


# --- Request For Quotation (RFQ) ---
class RFQSupplierInvite(BaseModel):
    supplier_id: uuid.UUID


class RFQSupplierResponse(BaseModel):
    id: uuid.UUID
    rfq_id: uuid.UUID
    supplier_id: uuid.UUID
    invited_at: datetime
    status: str
    supplier_name: Optional[str] = None
    supplier_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RFQCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=150)
    requisition_id: Optional[uuid.UUID] = None
    submission_deadline: datetime
    terms_and_conditions: Optional[str] = None
    notes: Optional[str] = None
    supplier_ids: Optional[List[uuid.UUID]] = None


class RFQUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=150)
    submission_deadline: Optional[datetime] = None
    terms_and_conditions: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = Field(None, description="Draft, Issued, Closed, Cancelled")


class RFQResponse(BaseModel):
    id: uuid.UUID
    rfq_number: str
    title: str
    requisition_id: Optional[uuid.UUID] = None
    submission_deadline: datetime
    status: str
    terms_and_conditions: Optional[str] = None
    notes: Optional[str] = None
    invited_suppliers: List[RFQSupplierResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedRFQResponse(BaseModel):
    items: List[RFQResponse]
    total: int
    page: int
    size: int
    pages: int


class RFQComparisonMatrix(BaseModel):
    rfq_id: uuid.UUID
    rfq_number: str
    title: str
    quotations_count: int
    comparison_items: List[Dict[str, Any]]


# --- Supplier Quotations ---
class SupplierQuotationItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    discount_pct: Decimal = Field(Decimal("0.0"), ge=0, le=100)
    tax_pct: Decimal = Field(Decimal("0.0"), ge=0, le=100)
    delivery_days: Optional[int] = None
    remarks: Optional[str] = None


class SupplierQuotationItemResponse(BaseModel):
    id: uuid.UUID
    quotation_id: uuid.UUID
    product_id: uuid.UUID
    quantity: Decimal
    unit_price: Decimal
    discount_pct: Decimal
    tax_pct: Decimal
    total_price: Decimal
    delivery_days: Optional[int] = None
    remarks: Optional[str] = None
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupplierQuotationCreate(BaseModel):
    rfq_id: Optional[uuid.UUID] = None
    supplier_id: uuid.UUID
    quotation_date: Optional[datetime] = None
    validity_date: datetime
    lead_time_days: int = Field(7, ge=1)
    payment_terms: Optional[str] = None
    currency: str = "USD"
    notes: Optional[str] = None
    items: List[SupplierQuotationItemCreate]


class SupplierQuotationUpdate(BaseModel):
    validity_date: Optional[datetime] = None
    lead_time_days: Optional[int] = None
    payment_terms: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = Field(None, description="Draft, Submitted, Under Review, Approved, Rejected, Expired")


class SupplierQuotationResponse(BaseModel):
    id: uuid.UUID
    quotation_number: str
    rfq_id: Optional[uuid.UUID] = None
    supplier_id: uuid.UUID
    quotation_date: datetime
    validity_date: datetime
    lead_time_days: int
    payment_terms: Optional[str] = None
    currency: str
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    status: str
    notes: Optional[str] = None
    supplier_name: Optional[str] = None
    items: List[SupplierQuotationItemResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedSupplierQuotationResponse(BaseModel):
    items: List[SupplierQuotationResponse]
    total: int
    page: int
    size: int
    pages: int


# --- Purchase Orders ---
class PurchaseOrderItemCreate(BaseModel):
    product_id: uuid.UUID
    description: Optional[str] = None
    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    discount_pct: Decimal = Field(Decimal("0.0"), ge=0, le=100)
    tax_pct: Decimal = Field(Decimal("0.0"), ge=0, le=100)
    warehouse_id: uuid.UUID
    storage_location_id: Optional[uuid.UUID] = None
    expected_delivery_date: Optional[datetime] = None


class PurchaseOrderItemResponse(BaseModel):
    id: uuid.UUID
    purchase_order_id: uuid.UUID
    product_id: uuid.UUID
    description: Optional[str] = None
    quantity: Decimal
    received_quantity: Decimal
    returned_quantity: Decimal
    unit_price: Decimal
    discount_pct: Decimal
    tax_pct: Decimal
    total_price: Decimal
    warehouse_id: uuid.UUID
    storage_location_id: Optional[uuid.UUID] = None
    expected_delivery_date: Optional[datetime] = None
    status: str
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    warehouse_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderCreate(BaseModel):
    origin_type: str = Field("Manual", description="Manual, Requisition, RFQ, Quotation")
    origin_document_id: Optional[uuid.UUID] = None
    supplier_id: uuid.UUID
    order_date: Optional[datetime] = None
    expected_delivery_date: Optional[datetime] = None
    payment_terms: Optional[str] = None
    currency: str = "USD"
    shipping_address: Optional[str] = None
    billing_address: Optional[str] = None
    notes: Optional[str] = None
    items: List[PurchaseOrderItemCreate]


class PurchaseOrderUpdate(BaseModel):
    supplier_id: Optional[uuid.UUID] = None
    order_date: Optional[datetime] = None
    expected_delivery_date: Optional[datetime] = None
    payment_terms: Optional[str] = None
    currency: Optional[str] = None
    shipping_address: Optional[str] = None
    billing_address: Optional[str] = None
    notes: Optional[str] = None
    items: Optional[List[PurchaseOrderItemCreate]] = None


class PurchaseOrderAmend(BaseModel):
    expected_delivery_date: Optional[datetime] = None
    payment_terms: Optional[str] = None
    shipping_address: Optional[str] = None
    billing_address: Optional[str] = None
    notes: Optional[str] = None
    amendment_reason: Optional[str] = None
    items: Optional[List[PurchaseOrderItemCreate]] = None


class PurchaseOrderFromQuotationCreate(BaseModel):
    warehouse_id: uuid.UUID
    expected_delivery_date: Optional[datetime] = None
    shipping_address: Optional[str] = None
    billing_address: Optional[str] = None
    notes: Optional[str] = None


class PurchaseOrderResponse(BaseModel):
    id: uuid.UUID
    po_number: str
    origin_type: str
    origin_document_id: Optional[uuid.UUID] = None
    supplier_id: uuid.UUID
    order_date: datetime
    expected_delivery_date: Optional[datetime] = None
    payment_terms: Optional[str] = None
    currency: str
    shipping_address: Optional[str] = None
    billing_address: Optional[str] = None
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    status: str
    revision_number: int
    created_by: Optional[uuid.UUID] = None
    approved_by: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None
    notes: Optional[str] = None
    supplier_name: Optional[str] = None
    items: List[PurchaseOrderItemResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedPurchaseOrderResponse(BaseModel):
    items: List[PurchaseOrderResponse]
    total: int
    page: int
    size: int
    pages: int


# --- Purchase Returns ---
class PurchaseReturnItemCreate(BaseModel):
    po_item_id: uuid.UUID
    product_id: uuid.UUID
    return_quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    reason: Optional[str] = None


class PurchaseReturnItemResponse(BaseModel):
    id: uuid.UUID
    purchase_return_id: uuid.UUID
    po_item_id: uuid.UUID
    product_id: uuid.UUID
    return_quantity: Decimal
    unit_price: Decimal
    reason: Optional[str] = None
    product_sku: Optional[str] = None
    product_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PurchaseReturnCreate(BaseModel):
    purchase_order_id: uuid.UUID
    supplier_id: uuid.UUID
    warehouse_id: uuid.UUID
    reason_code: str = Field(..., description="Damaged, Defective, Incorrect Spec, Excess Delivery")
    supplier_return_ref: Optional[str] = None
    remarks: Optional[str] = None
    items: List[PurchaseReturnItemCreate]


class PurchaseReturnResponse(BaseModel):
    id: uuid.UUID
    return_number: str
    purchase_order_id: uuid.UUID
    supplier_id: uuid.UUID
    warehouse_id: uuid.UUID
    return_date: datetime
    reason_code: str
    supplier_return_ref: Optional[str] = None
    total_return_amount: Decimal
    status: str
    created_by: Optional[uuid.UUID] = None
    approved_by: Optional[uuid.UUID] = None
    remarks: Optional[str] = None
    supplier_name: Optional[str] = None
    warehouse_code: Optional[str] = None
    items: List[PurchaseReturnItemResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedPurchaseReturnResponse(BaseModel):
    items: List[PurchaseReturnResponse]
    total: int
    page: int
    size: int
    pages: int


# --- Analytics & Reports ---
class ProcurementDashboardSummary(BaseModel):
    total_purchase_spend: Decimal
    open_po_count: int
    open_requisitions_count: int
    active_suppliers_count: int
    delayed_orders_count: int
    spend_by_department: List[Dict[str, Any]] = []
    top_vendors: List[Dict[str, Any]] = []
    purchase_trends: List[Dict[str, Any]] = []


class PurchaseRegisterItem(BaseModel):
    po_number: str
    order_date: datetime
    supplier_name: str
    total_amount: Decimal
    status: str


class SupplierLedgerItem(BaseModel):
    supplier_id: uuid.UUID
    supplier_name: str
    total_orders: int
    total_spend: Decimal
    ontime_rate: Decimal
    quality_rate: Decimal


class GlobalProcurementSearchResponse(BaseModel):
    query: str
    suppliers: List[Dict[str, Any]] = []
    purchase_orders: List[Dict[str, Any]] = []
    rfqs: List[Dict[str, Any]] = []
    quotations: List[Dict[str, Any]] = []
    requisitions: List[Dict[str, Any]] = []


class ProcurementImportResult(BaseModel):
    success_count: int
    error_count: int
    errors: List[str] = []
