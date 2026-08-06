import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin


class AccountGroup(Base, UUIDMixin, TimestampMixin):
    """
    AccountGroup ORM Model.
    Hierarchical classification for Chart of Accounts (e.g. Current Assets, Fixed Assets, Liabilities, Equity, Revenue, Expenses).
    """
    __tablename__ = "account_groups"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Asset, Liability, Equity, Income, Expense",
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("account_groups.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    parent: Mapped[Optional["AccountGroup"]] = relationship("AccountGroup", remote_side="AccountGroup.id", back_populates="children")
    children: Mapped[List["AccountGroup"]] = relationship("AccountGroup", back_populates="parent", cascade="all, delete-orphan")
    accounts: Mapped[List["ChartOfAccount"]] = relationship("ChartOfAccount", back_populates="account_group")

    def __repr__(self) -> str:
        return f"<AccountGroup(code='{self.code}', name='{self.name}', category='{self.category}')>"


class ChartOfAccount(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    ChartOfAccount ORM Model.
    General Ledger Account Master entity.
    """
    __tablename__ = "chart_of_accounts"

    account_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    account_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Asset, Liability, Equity, Income, Expense",
    )
    account_group_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("account_groups.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chart_of_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    currency_code: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="System reserved account")
    is_control: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="Control account for sub-ledgers")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    current_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    account_group: Mapped[Optional["AccountGroup"]] = relationship("AccountGroup", back_populates="accounts")
    parent: Mapped[Optional["ChartOfAccount"]] = relationship("ChartOfAccount", remote_side="ChartOfAccount.id", back_populates="children")
    children: Mapped[List["ChartOfAccount"]] = relationship("ChartOfAccount", back_populates="parent")

    def __repr__(self) -> str:
        return f"<ChartOfAccount(code='{self.account_code}', name='{self.name}', balance={self.current_balance})>"


class FiscalYear(Base, UUIDMixin, TimestampMixin):
    """
    FiscalYear ORM Model.
    Represents an accounting fiscal year.
    """
    __tablename__ = "fiscal_years"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20),
        default="Draft",
        nullable=False,
        index=True,
        comment="Draft, Open, Closed",
    )

    # Relationships
    periods: Mapped[List["FiscalPeriod"]] = relationship("FiscalPeriod", back_populates="fiscal_year", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self) -> str:
        return f"<FiscalYear(code='{self.code}', status='{self.status}')>"


class FiscalPeriod(Base, UUIDMixin, TimestampMixin):
    """
    FiscalPeriod ORM Model.
    Sub-period (monthly/quarterly) within a Fiscal Year.
    """
    __tablename__ = "fiscal_periods"

    fiscal_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fiscal_years.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    period_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    # Relationships
    fiscal_year: Mapped["FiscalYear"] = relationship("FiscalYear", back_populates="periods")

    __table_args__ = (
        UniqueConstraint("fiscal_year_id", "period_number", name="uq_fiscal_year_period"),
    )

    def __repr__(self) -> str:
        return f"<FiscalPeriod(name='{self.name}', locked={self.is_locked}, closed={self.is_closed})>"


class Currency(Base, UUIDMixin, TimestampMixin):
    """
    Currency ORM Model.
    Currency master definitions.
    """
    __tablename__ = "currencies"

    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    is_base: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    decimal_places: Mapped[int] = mapped_column(Integer, default=2, nullable=False)

    def __repr__(self) -> str:
        return f"<Currency(code='{self.code}', is_base={self.is_base})>"


class ExchangeRate(Base, UUIDMixin, TimestampMixin):
    """
    ExchangeRate ORM Model.
    Historical and daily exchange rates for multi-currency conversion.
    """
    __tablename__ = "exchange_rates"

    from_currency_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    to_currency_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    effective_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(50), default="Manual", nullable=False, comment="Manual, System, API")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("from_currency_code", "to_currency_code", "effective_date", name="uq_exchange_rate_date"),
    )

    def __repr__(self) -> str:
        return f"<ExchangeRate({self.from_currency_code}->{self.to_currency_code}: {self.rate} @ {self.effective_date})>"


class CostCenter(Base, UUIDMixin, TimestampMixin):
    """
    CostCenter ORM Model.
    Cost center allocation hierarchy.
    """
    __tablename__ = "cost_centers"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cost_centers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    business_unit: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    parent: Mapped[Optional["CostCenter"]] = relationship("CostCenter", remote_side="CostCenter.id", back_populates="children")
    children: Mapped[List["CostCenter"]] = relationship("CostCenter", back_populates="parent")

    def __repr__(self) -> str:
        return f"<CostCenter(code='{self.code}', name='{self.name}')>"


class AccountingDimension(Base, UUIDMixin, TimestampMixin):
    """
    AccountingDimension ORM Model.
    Configurable custom dimension for analytical accounting.
    """
    __tablename__ = "accounting_dimensions"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    dimension_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Department, Branch, Location, CostCenter, Project, Custom",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<AccountingDimension(name='{self.name}', type='{self.dimension_type}')>"


class JournalType(Base, UUIDMixin, TimestampMixin):
    """
    JournalType ORM Model.
    Master journal type definitions (General, Payroll, Purchase, Sales, Inventory, Adjustment, Opening, Closing).
    """
    __tablename__ = "journal_types"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    prefix: Mapped[str] = mapped_column(String(10), nullable=False, default="JV")
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approval_threshold: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)

    def __repr__(self) -> str:
        return f"<JournalType(code='{self.code}', prefix='{self.prefix}')>"


class Journal(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Journal ORM Model.
    General Ledger Header document representing double-entry postings.
    """
    __tablename__ = "journals"

    journal_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    journal_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("journal_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    posting_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    fiscal_period_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fiscal_periods.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    currency_code: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    exchange_rate: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("1.000000"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reference_module: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    reference_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(30),
        default="Draft",
        nullable=False,
        index=True,
        comment="Draft, PendingApproval, Approved, Posted, Cancelled, Reversed",
    )
    total_debit: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    total_credit: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    posted_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    posted_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reversed_journal_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("journals.id", ondelete="SET NULL"),
        nullable=True,
    )
    reversal_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    journal_type: Mapped["JournalType"] = relationship("JournalType")
    fiscal_period: Mapped[Optional["FiscalPeriod"]] = relationship("FiscalPeriod")
    lines: Mapped[List["JournalLine"]] = relationship("JournalLine", back_populates="journal", cascade="all, delete-orphan")
    posted_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[posted_by_id])  # noqa: F821
    approved_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by_id])  # noqa: F821
    reversed_journal: Mapped[Optional["Journal"]] = relationship("Journal", remote_side="Journal.id")

    def __repr__(self) -> str:
        return f"<Journal(number='{self.journal_number}', status='{self.status}', amount={self.total_debit})>"


class JournalLine(Base, UUIDMixin, TimestampMixin):
    """
    JournalLine ORM Model.
    Detail debit/credit line item for a Journal.
    """
    __tablename__ = "journal_lines"

    journal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("journals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chart_of_accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    cost_center_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cost_centers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    debit: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    credit: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dimensions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True, comment="Custom dimension values")
    reconciled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    journal: Mapped["Journal"] = relationship("Journal", back_populates="lines")
    account: Mapped["ChartOfAccount"] = relationship("ChartOfAccount")
    cost_center: Mapped[Optional["CostCenter"]] = relationship("CostCenter")

    def __repr__(self) -> str:
        return f"<JournalLine(line={self.line_number}, debit={self.debit}, credit={self.credit})>"


class TaxCategory(Base, UUIDMixin, TimestampMixin):
    """
    TaxCategory ORM Model.
    Master Tax category classification (VAT, Sales Tax, GST, Excise).
    """
    __tablename__ = "tax_categories"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    tax_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="Sales, Purchase, Output, Input")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    rates: Mapped[List["TaxRate"]] = relationship("TaxRate", back_populates="tax_category", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<TaxCategory(code='{self.code}', name='{self.name}')>"


class TaxRate(Base, UUIDMixin, TimestampMixin):
    """
    TaxRate ORM Model.
    Effective tax rates with GL tax account linking and validity windows.
    """
    __tablename__ = "tax_rates"

    tax_category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tax_categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    rate_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    effective_from: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    effective_to: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True, index=True)
    account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chart_of_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tax_category: Mapped["TaxCategory"] = relationship("TaxCategory", back_populates="rates")
    account: Mapped[Optional["ChartOfAccount"]] = relationship("ChartOfAccount")

    def __repr__(self) -> str:
        return f"<TaxRate(code='{self.code}', rate={self.rate_percentage}%)>"


class PostingRule(Base, UUIDMixin, TimestampMixin):
    """
    PostingRule ORM Model.
    Maps ERP operational domain events to automated General Ledger Journal Templates.
    """
    __tablename__ = "posting_rules"

    event_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="PayrollCompleted, PurchaseReceived, SalesDelivered, InventoryAdjustment, GoodsIssue, GoodsReceipt",
    )
    rule_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    journal_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("journal_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    debit_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chart_of_accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    credit_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chart_of_accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    tax_category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tax_categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    conditions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True, comment="Evaluation rule parameters")

    journal_type: Mapped["JournalType"] = relationship("JournalType")
    debit_account: Mapped["ChartOfAccount"] = relationship("ChartOfAccount", foreign_keys=[debit_account_id])
    credit_account: Mapped["ChartOfAccount"] = relationship("ChartOfAccount", foreign_keys=[credit_account_id])
    tax_category: Mapped[Optional["TaxCategory"]] = relationship("TaxCategory")

    def __repr__(self) -> str:
        return f"<PostingRule(code='{self.rule_code}', event='{self.event_name}')>"


class AccountingEvent(Base, UUIDMixin, TimestampMixin):
    """
    AccountingEvent ORM Model.
    Audit log record for financial events.
    """
    __tablename__ = "accounting_events"

    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    def __repr__(self) -> str:
        return f"<AccountingEvent(type='{self.event_type}', entity='{self.entity_type}:{self.entity_id}')>"
