import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
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
from app.db.mixins import TimestampMixin, UUIDMixin


# ==========================================
# 1. Accounts Receivable & Customer Ledger
# ==========================================

class CustomerInvoice(Base, UUIDMixin, TimestampMixin):
    """
    Customer Invoice ORM Model.
    Represents an Accounts Receivable sales invoice issued to a customer.
    """
    __tablename__ = "customer_invoices"

    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    sales_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    journal_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journals.id", ondelete="SET NULL"), nullable=True, index=True
    )
    invoice_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    due_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    currency_code: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    exchange_rate: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("1.000000"), nullable=False)

    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    outstanding_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)

    status: Mapped[str] = mapped_column(
        String(20),
        default="Draft",
        nullable=False,
        index=True,
        comment="Draft, Posted, PartiallyPaid, Paid, Cancelled",
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", lazy="selectin")
    lines: Mapped[List["CustomerInvoiceLine"]] = relationship(
        "CustomerInvoiceLine", back_populates="invoice", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<CustomerInvoice(number='{self.invoice_number}', status='{self.status}', total={self.total_amount})>"


class CustomerInvoiceLine(Base, UUIDMixin, TimestampMixin):
    """
    Customer Invoice Line Item ORM Model.
    """
    __tablename__ = "customer_invoice_lines"

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customer_invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chart_of_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("1.0000"), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0.0000"), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    tax_rate_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tax_rates.id", ondelete="SET NULL"), nullable=True
    )
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)

    invoice: Mapped["CustomerInvoice"] = relationship("CustomerInvoice", back_populates="lines")


class CustomerCreditNote(Base, UUIDMixin, TimestampMixin):
    """
    Customer Credit Note ORM Model.
    """
    __tablename__ = "customer_credit_notes"

    note_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    invoice_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customer_invoices.id", ondelete="SET NULL"), nullable=True
    )
    journal_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journals.id", ondelete="SET NULL"), nullable=True
    )
    issue_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Draft", nullable=False, index=True)


class CustomerDebitNote(Base, UUIDMixin, TimestampMixin):
    """
    Customer Debit Note ORM Model.
    """
    __tablename__ = "customer_debit_notes"

    note_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    invoice_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customer_invoices.id", ondelete="SET NULL"), nullable=True
    )
    journal_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journals.id", ondelete="SET NULL"), nullable=True
    )
    issue_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Draft", nullable=False, index=True)


class CustomerLedgerEntry(Base, UUIDMixin, TimestampMixin):
    """
    Customer Sub-Ledger Entry ORM Model.
    Tracks all customer debits, credits, and running balance.
    """
    __tablename__ = "customer_ledger_entries"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    posting_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(
        String(30), nullable=False, comment="Invoice, Receipt, CreditNote, DebitNote, Adjustment"
    )
    document_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    journal_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journals.id", ondelete="SET NULL"), nullable=True
    )
    debit: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    credit: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    running_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


# ==========================================
# 2. Accounts Payable & Supplier Ledger
# ==========================================

class SupplierBill(Base, UUIDMixin, TimestampMixin):
    """
    Supplier Bill ORM Model.
    Represents an Accounts Payable vendor bill received from a supplier.
    """
    __tablename__ = "supplier_bills"

    bill_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    vendor_bill_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    purchase_order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    journal_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journals.id", ondelete="SET NULL"), nullable=True, index=True
    )
    bill_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    due_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    currency_code: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    exchange_rate: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=Decimal("1.000000"), nullable=False)

    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    outstanding_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)

    status: Mapped[str] = mapped_column(
        String(20),
        default="Draft",
        nullable=False,
        index=True,
        comment="Draft, Posted, PartiallyPaid, Paid, Cancelled",
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    supplier: Mapped["Supplier"] = relationship("Supplier", lazy="selectin")
    lines: Mapped[List["SupplierBillLine"]] = relationship(
        "SupplierBillLine", back_populates="bill", cascade="all, delete-orphan", lazy="selectin"
    )


class SupplierBillLine(Base, UUIDMixin, TimestampMixin):
    """
    Supplier Bill Line Item ORM Model.
    """
    __tablename__ = "supplier_bill_lines"

    bill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supplier_bills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chart_of_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("1.0000"), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0.0000"), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    tax_rate_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tax_rates.id", ondelete="SET NULL"), nullable=True
    )
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)

    bill: Mapped["SupplierBill"] = relationship("SupplierBill", back_populates="lines")


class SupplierCreditNote(Base, UUIDMixin, TimestampMixin):
    """
    Supplier Credit Note ORM Model.
    """
    __tablename__ = "supplier_credit_notes"

    note_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    bill_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supplier_bills.id", ondelete="SET NULL"), nullable=True
    )
    journal_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journals.id", ondelete="SET NULL"), nullable=True
    )
    issue_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Draft", nullable=False, index=True)


class SupplierDebitNote(Base, UUIDMixin, TimestampMixin):
    """
    Supplier Debit Note ORM Model.
    """
    __tablename__ = "supplier_debit_notes"

    note_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    bill_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supplier_bills.id", ondelete="SET NULL"), nullable=True
    )
    journal_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journals.id", ondelete="SET NULL"), nullable=True
    )
    issue_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Draft", nullable=False, index=True)


class SupplierLedgerEntry(Base, UUIDMixin, TimestampMixin):
    """
    Supplier Sub-Ledger Entry ORM Model.
    Tracks all supplier debits, credits, and running balance.
    """
    __tablename__ = "supplier_ledger_entries"

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    posting_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(
        String(30), nullable=False, comment="Bill, Payment, DebitNote, CreditNote, Adjustment"
    )
    document_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    journal_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journals.id", ondelete="SET NULL"), nullable=True
    )
    debit: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    credit: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    running_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


# ==========================================
# 3. Payments & Payment Allocations
# ==========================================

class ReceiptVoucher(Base, UUIDMixin, TimestampMixin):
    """
    Receipt Voucher ORM Model.
    Represents customer inbound payment receipts or miscellaneous receipts.
    """
    __tablename__ = "receipt_vouchers"

    voucher_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    payment_mode: Mapped[str] = mapped_column(String(20), nullable=False, comment="Cash, Bank, Electronic")
    bank_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bank_accounts.id", ondelete="SET NULL"), nullable=True
    )
    cash_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chart_of_accounts.id", ondelete="SET NULL"), nullable=True
    )
    journal_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journals.id", ondelete="SET NULL"), nullable=True
    )
    receipt_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    allocated_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    unallocated_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    reference_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="Draft", nullable=False, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    allocations: Mapped[List["PaymentAllocation"]] = relationship(
        "PaymentAllocation", foreign_keys="PaymentAllocation.receipt_voucher_id", cascade="all, delete-orphan", lazy="selectin"
    )


class PaymentVoucher(Base, UUIDMixin, TimestampMixin):
    """
    Payment Voucher ORM Model.
    Represents supplier outbound payments or expense disbursements.
    """
    __tablename__ = "payment_vouchers"

    voucher_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    supplier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    payment_mode: Mapped[str] = mapped_column(String(20), nullable=False, comment="Cash, Bank, Electronic")
    bank_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bank_accounts.id", ondelete="SET NULL"), nullable=True
    )
    cash_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chart_of_accounts.id", ondelete="SET NULL"), nullable=True
    )
    journal_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journals.id", ondelete="SET NULL"), nullable=True
    )
    payment_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    allocated_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    unallocated_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    reference_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="Draft", nullable=False, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    allocations: Mapped[List["PaymentAllocation"]] = relationship(
        "PaymentAllocation", foreign_keys="PaymentAllocation.payment_voucher_id", cascade="all, delete-orphan", lazy="selectin"
    )


class PaymentAllocation(Base, UUIDMixin, TimestampMixin):
    """
    Payment Allocation ORM Model.
    Maps Payment/Receipt vouchers to specific Invoices, Bills, or Credit/Debit Notes.
    """
    __tablename__ = "payment_allocations"

    receipt_voucher_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("receipt_vouchers.id", ondelete="CASCADE"), nullable=True, index=True
    )
    payment_voucher_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payment_vouchers.id", ondelete="CASCADE"), nullable=True, index=True
    )
    customer_invoice_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customer_invoices.id", ondelete="CASCADE"), nullable=True, index=True
    )
    supplier_bill_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supplier_bills.id", ondelete="CASCADE"), nullable=True, index=True
    )
    allocation_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    allocation_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)


# ==========================================
# 4. Bank Management & Reconciliation
# ==========================================

class BankAccount(Base, UUIDMixin, TimestampMixin):
    """
    Company Bank Account ORM Model.
    """
    __tablename__ = "bank_accounts"

    account_name: Mapped[str] = mapped_column(String(100), nullable=False)
    account_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    bank_name: Mapped[str] = mapped_column(String(100), nullable=False)
    branch_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    swift_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    iban: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    currency_code: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    gl_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chart_of_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    current_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    gl_account: Mapped["ChartOfAccount"] = relationship("ChartOfAccount", lazy="selectin")


class BankTransaction(Base, UUIDMixin, TimestampMixin):
    """
    Bank Transaction ORM Model.
    """
    __tablename__ = "bank_transactions"

    bank_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bank_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    transaction_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    transaction_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Deposit, Withdrawal, Fee, Cheque"
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    reference_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    payee_or_payer: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    journal_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journals.id", ondelete="SET NULL"), nullable=True
    )
    is_reconciled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)


class BankStatement(Base, UUIDMixin, TimestampMixin):
    """
    Imported Bank Statement ORM Model.
    """
    __tablename__ = "bank_statements"

    bank_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bank_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    statement_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    start_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    end_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    closing_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Uploaded", nullable=False, index=True)

    lines: Mapped[List["BankStatementLine"]] = relationship(
        "BankStatementLine", back_populates="statement", cascade="all, delete-orphan", lazy="selectin"
    )


class BankStatementLine(Base, UUIDMixin, TimestampMixin):
    """
    Bank Statement Line Item.
    """
    __tablename__ = "bank_statement_lines"

    statement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bank_statements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    transaction_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    reference_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_matched: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    matched_transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bank_transactions.id", ondelete="SET NULL"), nullable=True
    )

    statement: Mapped["BankStatement"] = relationship("BankStatement", back_populates="lines")


class BankReconciliation(Base, UUIDMixin, TimestampMixin):
    """
    Bank Reconciliation Record ORM Model.
    """
    __tablename__ = "bank_reconciliations"

    bank_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bank_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reconciliation_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    statement_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    gl_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    unreconciled_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Draft", nullable=False, index=True)

    items: Mapped[List["BankReconciliationItem"]] = relationship(
        "BankReconciliationItem", back_populates="reconciliation", cascade="all, delete-orphan", lazy="selectin"
    )


class BankReconciliationItem(Base, UUIDMixin, TimestampMixin):
    """
    Bank Reconciliation Item Detail.
    """
    __tablename__ = "bank_reconciliation_items"

    reconciliation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bank_reconciliations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    statement_line_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bank_statement_lines.id", ondelete="SET NULL"), nullable=True
    )
    bank_transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bank_transactions.id", ondelete="SET NULL"), nullable=True
    )
    match_status: Mapped[str] = mapped_column(String(20), default="Matched", nullable=False)

    reconciliation: Mapped["BankReconciliation"] = relationship("BankReconciliation", back_populates="items")


# ==========================================
# 5. Fixed Assets & Depreciation
# ==========================================

class AssetCategory(Base, UUIDMixin, TimestampMixin):
    """
    Asset Category ORM Model.
    """
    __tablename__ = "asset_categories"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    depreciation_method: Mapped[str] = mapped_column(
        String(30), default="StraightLine", nullable=False, comment="StraightLine, WrittenDownValue"
    )
    useful_life_years: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    asset_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chart_of_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    accumulated_depreciation_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chart_of_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    depreciation_expense_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chart_of_accounts.id", ondelete="RESTRICT"), nullable=False
    )


class FixedAsset(Base, UUIDMixin, TimestampMixin):
    """
    Fixed Asset ORM Model.
    """
    __tablename__ = "fixed_assets"

    asset_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("asset_categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    acquisition_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    purchase_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    salvage_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    current_book_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="Active", nullable=False, index=True, comment="Active, Disposed, UnderMaintenance"
    )

    category: Mapped["AssetCategory"] = relationship("AssetCategory", lazy="selectin")
    schedules: Mapped[List["DepreciationSchedule"]] = relationship(
        "DepreciationSchedule", back_populates="asset", cascade="all, delete-orphan", lazy="selectin"
    )


class DepreciationSchedule(Base, UUIDMixin, TimestampMixin):
    """
    Depreciation Schedule Entry ORM Model.
    """
    __tablename__ = "depreciation_schedules"

    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fixed_assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    schedule_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    period_name: Mapped[str] = mapped_column(String(20), nullable=False)
    depreciation_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    accumulated_depreciation: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    ending_book_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Scheduled", nullable=False, index=True)
    journal_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("journals.id", ondelete="SET NULL"), nullable=True
    )

    asset: Mapped["FixedAsset"] = relationship("FixedAsset", back_populates="schedules")


# ==========================================
# 6. Budget Management
# ==========================================

class Budget(Base, UUIDMixin, TimestampMixin):
    """
    Budget Header ORM Model.
    """
    __tablename__ = "budgets"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    fiscal_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fiscal_years.id", ondelete="CASCADE"), nullable=False, index=True
    )
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )
    cost_center_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cost_centers.id", ondelete="SET NULL"), nullable=True
    )
    total_budgeted_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    total_actual_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="Draft", nullable=False, index=True, comment="Draft, Submitted, Approved, Closed"
    )

    lines: Mapped[List["BudgetLine"]] = relationship(
        "BudgetLine", back_populates="budget", cascade="all, delete-orphan", lazy="selectin"
    )


class BudgetLine(Base, UUIDMixin, TimestampMixin):
    """
    Budget Line Item ORM Model.
    """
    __tablename__ = "budget_lines"

    budget_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chart_of_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    budgeted_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    actual_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    variance_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)

    budget: Mapped["Budget"] = relationship("Budget", back_populates="lines")
    account: Mapped["ChartOfAccount"] = relationship("ChartOfAccount", lazy="selectin")


# ==========================================
# 7. Financial Statement Snapshots
# ==========================================

class FinancialStatementSnapshot(Base, UUIDMixin, TimestampMixin):
    """
    Financial Statement Telemetry & Audit Snapshot.
    """
    __tablename__ = "financial_statement_snapshots"

    statement_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="TrialBalance, BalanceSheet, ProfitAndLoss, CashFlow"
    )
    as_of_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    period_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fiscal_periods.id", ondelete="SET NULL"), nullable=True
    )
    data: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    generated_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
