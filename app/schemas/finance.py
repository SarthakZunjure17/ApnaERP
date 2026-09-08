from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field, model_validator


# --- Account Group Schemas ---
class AccountGroupBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    category: str = Field(..., max_length=50, description="Asset, Liability, Equity, Income, Expense")
    parent_id: Optional[uuid.UUID] = None
    display_order: int = 0


class AccountGroupCreate(AccountGroupBase):
    pass


class AccountGroupUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    parent_id: Optional[uuid.UUID] = None
    display_order: Optional[int] = None


class AccountGroupResponse(AccountGroupBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Chart of Accounts Schemas ---
class ChartOfAccountBase(BaseModel):
    account_code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=150)
    account_type: str = Field(..., max_length=50, description="Asset, Liability, Equity, Income, Expense")
    account_group_id: Optional[uuid.UUID] = None
    parent_id: Optional[uuid.UUID] = None
    currency_code: str = "USD"
    is_system: bool = False
    is_control: bool = False
    is_active: bool = True
    opening_balance: Decimal = Field(Decimal("0.00"))
    notes: Optional[str] = None


class ChartOfAccountCreate(ChartOfAccountBase):
    pass


class ChartOfAccountUpdate(BaseModel):
    name: Optional[str] = None
    account_type: Optional[str] = None
    account_group_id: Optional[uuid.UUID] = None
    parent_id: Optional[uuid.UUID] = None
    currency_code: Optional[str] = None
    is_active: Optional[bool] = None
    opening_balance: Optional[Decimal] = None
    notes: Optional[str] = None


class ChartOfAccountResponse(ChartOfAccountBase):
    id: uuid.UUID
    current_balance: Decimal
    created_at: datetime
    updated_at: datetime
    account_group: Optional[AccountGroupResponse] = None
    model_config = ConfigDict(from_attributes=True)


# --- Fiscal Year & Period Schemas ---
class FiscalYearBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    start_date: date
    end_date: date
    status: str = "Draft"


class FiscalYearCreate(FiscalYearBase):
    pass


class FiscalPeriodBase(BaseModel):
    fiscal_year_id: uuid.UUID
    period_number: int
    name: str = Field(..., max_length=100)
    start_date: date
    end_date: date
    is_locked: bool = False
    is_closed: bool = False


class FiscalPeriodCreate(FiscalPeriodBase):
    pass


class FiscalPeriodLockRequest(BaseModel):
    is_locked: bool


class FiscalPeriodResponse(FiscalPeriodBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class FiscalYearResponse(FiscalYearBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    periods: List[FiscalPeriodResponse] = []
    model_config = ConfigDict(from_attributes=True)


# --- Currency & Exchange Rate Schemas ---
class CurrencyBase(BaseModel):
    code: str = Field(..., max_length=10)
    name: str = Field(..., max_length=100)
    symbol: str = Field(..., max_length=10)
    is_base: bool = False
    is_active: bool = True
    decimal_places: int = 2


class CurrencyCreate(CurrencyBase):
    pass


class CurrencyResponse(CurrencyBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ExchangeRateBase(BaseModel):
    from_currency_code: str = Field(..., max_length=10)
    to_currency_code: str = Field(..., max_length=10)
    rate: Decimal = Field(..., gt=0)
    effective_date: date
    source: str = "Manual"
    is_active: bool = True


class ExchangeRateCreate(ExchangeRateBase):
    pass


class ExchangeRateResponse(ExchangeRateBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ExchangeRateConvertRequest(BaseModel):
    from_currency: str
    to_currency: str
    amount: Decimal
    effective_date: Optional[date] = None


# --- Cost Center & Accounting Dimension Schemas ---
class CostCenterBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=150)
    parent_id: Optional[uuid.UUID] = None
    department_id: Optional[uuid.UUID] = None
    business_unit: Optional[str] = None
    is_active: bool = True


class CostCenterCreate(CostCenterBase):
    pass


class CostCenterUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[uuid.UUID] = None
    department_id: Optional[uuid.UUID] = None
    business_unit: Optional[str] = None
    is_active: Optional[bool] = None


class CostCenterResponse(CostCenterBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AccountingDimensionBase(BaseModel):
    name: str = Field(..., max_length=100)
    dimension_type: str = Field(..., max_length=50)
    is_active: bool = True
    is_required: bool = False


class AccountingDimensionCreate(AccountingDimensionBase):
    pass


class AccountingDimensionResponse(AccountingDimensionBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Journal Type Schemas ---
class JournalTypeBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    prefix: str = "JV"
    requires_approval: bool = False
    approval_threshold: Decimal = Field(Decimal("0.00"), ge=0)


class JournalTypeCreate(JournalTypeBase):
    pass


class JournalTypeResponse(JournalTypeBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Journal Line & Journal Schemas ---
class JournalLineBase(BaseModel):
    account_id: uuid.UUID
    cost_center_id: Optional[uuid.UUID] = None
    debit: Decimal = Field(Decimal("0.00"), ge=0)
    credit: Decimal = Field(Decimal("0.00"), ge=0)
    description: Optional[str] = None
    dimensions: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def validate_debit_or_credit(self):
        if self.debit == 0 and self.credit == 0:
            raise ValueError("Journal line must have either debit or credit greater than 0")
        if self.debit > 0 and self.credit > 0:
            raise ValueError("Journal line cannot have both debit and credit greater than 0")
        return self


class JournalLineCreate(JournalLineBase):
    pass


class JournalLineResponse(JournalLineBase):
    id: uuid.UUID
    line_number: int
    reconciled: bool
    account: Optional[ChartOfAccountResponse] = None
    cost_center: Optional[CostCenterResponse] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class JournalBase(BaseModel):
    journal_type_id: uuid.UUID
    posting_date: date
    fiscal_period_id: Optional[uuid.UUID] = None
    currency_code: str = "USD"
    exchange_rate: Decimal = Field(Decimal("1.000000"), gt=0)
    description: str
    reference_module: Optional[str] = None
    reference_id: Optional[str] = None


class JournalCreate(JournalBase):
    lines: List[JournalLineCreate]

    @model_validator(mode="after")
    def validate_double_entry_balance(self):
        if not self.lines or len(self.lines) < 2:
            raise ValueError("Journal entry must contain at least 2 line items for double-entry accounting")

        total_debit = sum(line.debit for line in self.lines)
        total_credit = sum(line.credit for line in self.lines)

        if total_debit != total_credit:
            raise ValueError(f"Unbalanced Journal: Total Debit ({total_debit}) must equal Total Credit ({total_credit})")
        if total_debit <= 0:
            raise ValueError("Total Journal Debit/Credit must be greater than 0")

        return self


class JournalUpdate(BaseModel):
    journal_type_id: Optional[uuid.UUID] = None
    posting_date: Optional[date] = None
    currency_code: Optional[str] = None
    exchange_rate: Optional[Decimal] = None
    description: Optional[str] = None
    reference_module: Optional[str] = None
    reference_id: Optional[str] = None
    lines: Optional[List[JournalLineCreate]] = None


class JournalResponse(JournalBase):
    id: uuid.UUID
    journal_number: str
    status: str
    total_debit: Decimal
    total_credit: Decimal
    posted_at: Optional[datetime] = None
    posted_by_id: Optional[uuid.UUID] = None
    reversed_journal_id: Optional[uuid.UUID] = None
    reversal_reason: Optional[str] = None
    approved_by_id: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None
    lines: List[JournalLineResponse] = []
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class JournalPostRequest(BaseModel):
    pass


class JournalReverseRequest(BaseModel):
    reason: str = Field(..., min_length=3)


# --- Tax Schemas ---
class TaxCategoryBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    tax_type: str = Field(..., max_length=50)
    description: Optional[str] = None
    is_active: bool = True


class TaxCategoryCreate(TaxCategoryBase):
    pass


class TaxCategoryResponse(TaxCategoryBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TaxRateBase(BaseModel):
    tax_category_id: uuid.UUID
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    rate_percentage: Decimal = Field(..., ge=0, le=100)
    effective_from: date
    effective_to: Optional[date] = None
    account_id: Optional[uuid.UUID] = None
    is_active: bool = True


class TaxRateCreate(TaxRateBase):
    pass


class TaxRateResponse(TaxRateBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    tax_category: Optional[TaxCategoryResponse] = None
    model_config = ConfigDict(from_attributes=True)


# --- Posting Rule Schemas ---
class PostingRuleBase(BaseModel):
    event_name: str = Field(..., max_length=100)
    rule_code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=150)
    journal_type_id: uuid.UUID
    debit_account_id: uuid.UUID
    credit_account_id: uuid.UUID
    tax_category_id: Optional[uuid.UUID] = None
    is_active: bool = True
    conditions: Optional[Dict[str, Any]] = None


class PostingRuleCreate(PostingRuleBase):
    pass


class PostingRuleResponse(PostingRuleBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Accounting Event Schemas ---
class AccountingEventResponse(BaseModel):
    id: uuid.UUID
    event_type: str
    event_name: str
    entity_type: str
    entity_id: uuid.UUID
    payload: Dict[str, Any]
    timestamp: datetime
    user_id: Optional[uuid.UUID] = None
    model_config = ConfigDict(from_attributes=True)


# --- Finance Search Response ---
class FinanceSearchResponse(BaseModel):
    accounts: List[ChartOfAccountResponse] = []
    journals: List[JournalResponse] = []
    cost_centers: List[CostCenterResponse] = []


# --- Company / Accounting Configuration Schemas ---
class CompanyBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=150)
    legal_name: Optional[str] = Field(None, max_length=200)
    tax_id: Optional[str] = Field(None, max_length=50)
    base_currency_code: str = Field("USD", max_length=10)
    fiscal_year_start_month: int = Field(1, ge=1, le=12)
    default_receivable_account_id: Optional[uuid.UUID] = None
    default_payable_account_id: Optional[uuid.UUID] = None
    default_retained_earnings_account_id: Optional[uuid.UUID] = None
    default_bank_account_id: Optional[uuid.UUID] = None
    default_cash_account_id: Optional[uuid.UUID] = None
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field("United States", max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=100)
    is_active: bool = True


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    legal_name: Optional[str] = None
    tax_id: Optional[str] = None
    base_currency_code: Optional[str] = None
    fiscal_year_start_month: Optional[int] = Field(None, ge=1, le=12)
    default_receivable_account_id: Optional[uuid.UUID] = None
    default_payable_account_id: Optional[uuid.UUID] = None
    default_retained_earnings_account_id: Optional[uuid.UUID] = None
    default_bank_account_id: Optional[uuid.UUID] = None
    default_cash_account_id: Optional[uuid.UUID] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None


class CompanyResponse(CompanyBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- General Ledger Schemas ---
class GeneralLedgerEntryResponse(BaseModel):
    id: uuid.UUID
    journal_id: uuid.UUID
    journal_number: str
    posting_date: date
    line_number: int
    account_id: uuid.UUID
    account_code: str
    account_name: str
    account_type: str
    debit: Decimal
    credit: Decimal
    running_balance: Optional[Decimal] = None
    description: Optional[str] = None
    reference_module: Optional[str] = None
    reference_id: Optional[str] = None
    cost_center_id: Optional[uuid.UUID] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AccountLedgerResponse(BaseModel):
    account_id: uuid.UUID
    account_code: str
    account_name: str
    account_type: str
    currency_code: str
    opening_balance: Decimal
    period_debit: Decimal
    period_credit: Decimal
    closing_balance: Decimal
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    entries: List[GeneralLedgerEntryResponse] = []
    total_entries: int = 0


class TrialBalanceLineResponse(BaseModel):
    account_id: uuid.UUID
    account_code: str
    account_name: str
    account_type: str
    opening_balance: Decimal = Decimal("0.00")
    period_debit: Decimal = Decimal("0.00")
    period_credit: Decimal = Decimal("0.00")
    debit_balance: Decimal = Decimal("0.00")
    credit_balance: Decimal = Decimal("0.00")
    net_balance: Decimal = Decimal("0.00")


class TrialBalanceReportResponse(BaseModel):
    as_of_date: date
    total_debit: Decimal
    total_credit: Decimal
    is_balanced: bool = True
    lines: List[TrialBalanceLineResponse] = []

