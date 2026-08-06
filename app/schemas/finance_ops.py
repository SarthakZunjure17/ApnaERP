import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ==========================================
# 1. Accounts Receivable & Customer Ledger DTOs
# ==========================================

class CustomerInvoiceLineCreate(BaseModel):
    product_id: Optional[uuid.UUID] = None
    account_id: uuid.UUID
    description: str
    quantity: Decimal = Field(default=Decimal("1.0000"), gt=0)
    unit_price: Decimal = Field(default=Decimal("0.0000"), ge=0)
    tax_rate_id: Optional[uuid.UUID] = None
    tax_amount: Decimal = Field(default=Decimal("0.00"), ge=0)


class CustomerInvoiceLineResponse(CustomerInvoiceLineCreate):
    id: uuid.UUID
    invoice_id: uuid.UUID
    subtotal: Decimal
    total_amount: Decimal

    model_config = ConfigDict(from_attributes=True)


class CustomerInvoiceCreate(BaseModel):
    customer_id: uuid.UUID
    sales_order_id: Optional[uuid.UUID] = None
    invoice_date: datetime.date
    due_date: datetime.date
    currency_code: str = "USD"
    exchange_rate: Decimal = Decimal("1.000000")
    notes: Optional[str] = None
    lines: List[CustomerInvoiceLineCreate] = Field(..., min_length=1)


class CustomerInvoiceResponse(BaseModel):
    id: uuid.UUID
    invoice_number: str
    customer_id: uuid.UUID
    sales_order_id: Optional[uuid.UUID]
    journal_id: Optional[uuid.UUID]
    invoice_date: datetime.date
    due_date: datetime.date
    currency_code: str
    exchange_rate: Decimal
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal
    status: str
    notes: Optional[str]
    created_at: datetime.datetime
    lines: List[CustomerInvoiceLineResponse] = []

    model_config = ConfigDict(from_attributes=True)


class CreditDebitNoteCreate(BaseModel):
    customer_id: uuid.UUID
    invoice_id: Optional[uuid.UUID] = None
    issue_date: datetime.date
    amount: Decimal = Field(..., gt=0)
    reason: str


class CreditDebitNoteResponse(CreditDebitNoteCreate):
    id: uuid.UUID
    note_number: str
    journal_id: Optional[uuid.UUID]
    status: str
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerLedgerEntryResponse(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    posting_date: datetime.date
    document_type: str
    document_number: str
    journal_id: Optional[uuid.UUID]
    debit: Decimal
    credit: Decimal
    running_balance: Decimal
    description: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class AgingBucket(BaseModel):
    current_0_30: Decimal = Decimal("0.00")
    days_31_60: Decimal = Decimal("0.00")
    days_61_90: Decimal = Decimal("0.00")
    over_90_days: Decimal = Decimal("0.00")
    total_outstanding: Decimal = Decimal("0.00")


class CustomerStatementResponse(BaseModel):
    customer_id: uuid.UUID
    customer_name: str
    as_of_date: datetime.date
    total_outstanding: Decimal
    aging: AgingBucket
    entries: List[CustomerLedgerEntryResponse] = []


# ==========================================
# 2. Accounts Payable & Supplier Ledger DTOs
# ==========================================

class SupplierBillLineCreate(BaseModel):
    product_id: Optional[uuid.UUID] = None
    account_id: uuid.UUID
    description: str
    quantity: Decimal = Field(default=Decimal("1.0000"), gt=0)
    unit_price: Decimal = Field(default=Decimal("0.0000"), ge=0)
    tax_rate_id: Optional[uuid.UUID] = None
    tax_amount: Decimal = Field(default=Decimal("0.00"), ge=0)


class SupplierBillLineResponse(SupplierBillLineCreate):
    id: uuid.UUID
    bill_id: uuid.UUID
    subtotal: Decimal
    total_amount: Decimal

    model_config = ConfigDict(from_attributes=True)


class SupplierBillCreate(BaseModel):
    supplier_id: uuid.UUID
    vendor_bill_number: Optional[str] = None
    purchase_order_id: Optional[uuid.UUID] = None
    bill_date: datetime.date
    due_date: datetime.date
    currency_code: str = "USD"
    exchange_rate: Decimal = Decimal("1.000000")
    notes: Optional[str] = None
    lines: List[SupplierBillLineCreate] = Field(..., min_length=1)


class SupplierBillResponse(BaseModel):
    id: uuid.UUID
    bill_number: str
    vendor_bill_number: Optional[str]
    supplier_id: uuid.UUID
    purchase_order_id: Optional[uuid.UUID]
    journal_id: Optional[uuid.UUID]
    bill_date: datetime.date
    due_date: datetime.date
    currency_code: str
    exchange_rate: Decimal
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal
    status: str
    notes: Optional[str]
    created_at: datetime.datetime
    lines: List[SupplierBillLineResponse] = []

    model_config = ConfigDict(from_attributes=True)


class SupplierLedgerEntryResponse(BaseModel):
    id: uuid.UUID
    supplier_id: uuid.UUID
    posting_date: datetime.date
    document_type: str
    document_number: str
    journal_id: Optional[uuid.UUID]
    debit: Decimal
    credit: Decimal
    running_balance: Decimal
    description: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class VendorStatementResponse(BaseModel):
    supplier_id: uuid.UUID
    supplier_name: str
    as_of_date: datetime.date
    total_outstanding: Decimal
    aging: AgingBucket
    entries: List[SupplierLedgerEntryResponse] = []


# ==========================================
# 3. Payments & Vouchers DTOs
# ==========================================

class AllocationCreate(BaseModel):
    customer_invoice_id: Optional[uuid.UUID] = None
    supplier_bill_id: Optional[uuid.UUID] = None
    allocation_amount: Decimal = Field(..., gt=0)


class ReceiptVoucherCreate(BaseModel):
    customer_id: Optional[uuid.UUID] = None
    payment_mode: str = Field(..., description="Cash, Bank, Electronic")
    bank_account_id: Optional[uuid.UUID] = None
    cash_account_id: Optional[uuid.UUID] = None
    receipt_date: datetime.date
    amount: Decimal = Field(..., gt=0)
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    allocations: List[AllocationCreate] = []


class ReceiptVoucherResponse(BaseModel):
    id: uuid.UUID
    voucher_number: str
    customer_id: Optional[uuid.UUID]
    payment_mode: str
    bank_account_id: Optional[uuid.UUID]
    cash_account_id: Optional[uuid.UUID]
    journal_id: Optional[uuid.UUID]
    receipt_date: datetime.date
    amount: Decimal
    allocated_amount: Decimal
    unallocated_amount: Decimal
    reference_number: Optional[str]
    status: str
    notes: Optional[str]
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class PaymentVoucherCreate(BaseModel):
    supplier_id: Optional[uuid.UUID] = None
    payment_mode: str = Field(..., description="Cash, Bank, Electronic")
    bank_account_id: Optional[uuid.UUID] = None
    cash_account_id: Optional[uuid.UUID] = None
    payment_date: datetime.date
    amount: Decimal = Field(..., gt=0)
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    allocations: List[AllocationCreate] = []


class PaymentVoucherResponse(BaseModel):
    id: uuid.UUID
    voucher_number: str
    supplier_id: Optional[uuid.UUID]
    payment_mode: str
    bank_account_id: Optional[uuid.UUID]
    cash_account_id: Optional[uuid.UUID]
    journal_id: Optional[uuid.UUID]
    payment_date: datetime.date
    amount: Decimal
    allocated_amount: Decimal
    unallocated_amount: Decimal
    reference_number: Optional[str]
    status: str
    notes: Optional[str]
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 4. Bank Management & Reconciliation DTOs
# ==========================================

class BankAccountCreate(BaseModel):
    account_name: str
    account_number: str
    bank_name: str
    branch_name: Optional[str] = None
    swift_code: Optional[str] = None
    iban: Optional[str] = None
    currency_code: str = "USD"
    gl_account_id: uuid.UUID


class BankAccountResponse(BankAccountCreate):
    id: uuid.UUID
    current_balance: Decimal
    is_active: bool
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class BankTransactionCreate(BaseModel):
    bank_account_id: uuid.UUID
    transaction_date: datetime.date
    transaction_type: str = Field(..., description="Deposit, Withdrawal, Fee, Cheque")
    amount: Decimal
    reference_number: Optional[str] = None
    payee_or_payer: Optional[str] = None
    description: Optional[str] = None


class BankTransactionResponse(BankTransactionCreate):
    id: uuid.UUID
    journal_id: Optional[uuid.UUID]
    is_reconciled: bool
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class BankStatementLineDTO(BaseModel):
    transaction_date: datetime.date
    amount: Decimal
    reference_number: Optional[str] = None
    description: Optional[str] = None


class BankStatementImportCreate(BaseModel):
    bank_account_id: uuid.UUID
    statement_number: str
    start_date: datetime.date
    end_date: datetime.date
    opening_balance: Decimal
    closing_balance: Decimal
    lines: List[BankStatementLineDTO] = []


class BankStatementResponse(BaseModel):
    id: uuid.UUID
    bank_account_id: uuid.UUID
    statement_number: str
    start_date: datetime.date
    end_date: datetime.date
    opening_balance: Decimal
    closing_balance: Decimal
    status: str
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class ManualMatchRequest(BaseModel):
    statement_line_id: uuid.UUID
    bank_transaction_id: uuid.UUID


class BankReconciliationResponse(BaseModel):
    id: uuid.UUID
    bank_account_id: uuid.UUID
    reconciliation_date: datetime.date
    statement_balance: Decimal
    gl_balance: Decimal
    unreconciled_amount: Decimal
    status: str
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 5. Fixed Assets & Depreciation DTOs
# ==========================================

class AssetCategoryCreate(BaseModel):
    code: str
    name: str
    depreciation_method: str = "StraightLine"
    useful_life_years: int = 5
    asset_account_id: uuid.UUID
    accumulated_depreciation_account_id: uuid.UUID
    depreciation_expense_account_id: uuid.UUID


class AssetCategoryResponse(AssetCategoryCreate):
    id: uuid.UUID
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class FixedAssetCreate(BaseModel):
    asset_code: str
    name: str
    category_id: uuid.UUID
    department_id: Optional[uuid.UUID] = None
    acquisition_date: datetime.date
    purchase_cost: Decimal = Field(..., gt=0)
    salvage_value: Decimal = Field(default=Decimal("0.00"), ge=0)


class FixedAssetResponse(BaseModel):
    id: uuid.UUID
    asset_code: str
    name: str
    category_id: uuid.UUID
    department_id: Optional[uuid.UUID]
    acquisition_date: datetime.date
    purchase_cost: Decimal
    salvage_value: Decimal
    current_book_value: Decimal
    status: str
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class DepreciationScheduleResponse(BaseModel):
    id: uuid.UUID
    asset_id: uuid.UUID
    schedule_date: datetime.date
    period_name: str
    depreciation_amount: Decimal
    accumulated_depreciation: Decimal
    ending_book_value: Decimal
    status: str
    journal_id: Optional[uuid.UUID]

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 6. Budget Management DTOs
# ==========================================

class BudgetLineCreate(BaseModel):
    account_id: uuid.UUID
    budgeted_amount: Decimal = Field(..., ge=0)


class BudgetLineResponse(BudgetLineCreate):
    id: uuid.UUID
    actual_amount: Decimal
    variance_amount: Decimal

    model_config = ConfigDict(from_attributes=True)


class BudgetCreate(BaseModel):
    code: str
    name: str
    fiscal_year_id: uuid.UUID
    department_id: Optional[uuid.UUID] = None
    cost_center_id: Optional[uuid.UUID] = None
    lines: List[BudgetLineCreate] = []


class BudgetResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    fiscal_year_id: uuid.UUID
    department_id: Optional[uuid.UUID]
    cost_center_id: Optional[uuid.UUID]
    total_budgeted_amount: Decimal
    total_actual_amount: Decimal
    status: str
    created_at: datetime.datetime
    lines: List[BudgetLineResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 7. Financial Statements & Reporting DTOs
# ==========================================

class TrialBalanceLine(BaseModel):
    account_code: str
    account_name: str
    account_type: str
    debit_balance: Decimal
    credit_balance: Decimal


class TrialBalanceResponse(BaseModel):
    as_of_date: datetime.date
    total_debit: Decimal
    total_credit: Decimal
    lines: List[TrialBalanceLine] = []


class BalanceSheetSection(BaseModel):
    section_name: str
    total_amount: Decimal
    accounts: List[Dict[str, Any]] = []


class BalanceSheetResponse(BaseModel):
    as_of_date: datetime.date
    total_assets: Decimal
    total_liabilities: Decimal
    total_equity: Decimal
    assets: BalanceSheetSection
    liabilities: BalanceSheetSection
    equity: BalanceSheetSection


class ProfitAndLossResponse(BaseModel):
    start_date: datetime.date
    end_date: datetime.date
    total_revenue: Decimal
    total_expense: Decimal
    net_profit: Decimal
    revenue_items: List[Dict[str, Any]] = []
    expense_items: List[Dict[str, Any]] = []


class CashFlowResponse(BaseModel):
    start_date: datetime.date
    end_date: datetime.date
    operating_activities: Decimal
    investing_activities: Decimal
    financing_activities: Decimal
    net_change_in_cash: Decimal
    beginning_cash_balance: Decimal
    ending_cash_balance: Decimal


class FinancialAnalyticsResponse(BaseModel):
    revenue: Decimal
    expenses: Decimal
    net_margin_percentage: Decimal
    cash_position: Decimal
    receivables_outstanding: Decimal
    payables_outstanding: Decimal
    asset_total_value: Decimal
    current_ratio: Decimal
    quick_ratio: Decimal
    debt_to_equity_ratio: Decimal
