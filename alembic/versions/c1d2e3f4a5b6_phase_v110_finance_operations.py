"""phase_v110_finance_operations

Revision ID: c1d2e3f4a5b6
Revises: b0c1d2e3f4a5
Create Date: 2026-08-06 16:36:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sqa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, None] = 'b0c1d2e3f4a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Accounts Receivable & Customer Ledger
    op.create_table(
        'customer_invoices',
        sqa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sqa.Column('invoice_number', sqa.String(50), nullable=False, unique=True),
        sqa.Column('customer_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('customers.id', ondelete='RESTRICT'), nullable=False),
        sqa.Column('sales_order_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('sales_orders.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('journal_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('journals.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('invoice_date', sqa.Date(), nullable=False),
        sqa.Column('due_date', sqa.Date(), nullable=False),
        sqa.Column('currency_code', sqa.String(10), nullable=False, server_default='USD'),
        sqa.Column('exchange_rate', sqa.Numeric(18, 6), nullable=False, server_default='1.000000'),
        sqa.Column('subtotal', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('tax_amount', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('total_amount', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('paid_amount', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('outstanding_amount', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('status', sqa.String(20), nullable=False, server_default='Draft'),
        sqa.Column('notes', sqa.Text(), nullable=True),
        sqa.Column('created_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
        sqa.Column('updated_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
    )
    op.create_index('ix_customer_invoices_invoice_number', 'customer_invoices', ['invoice_number'])
    op.create_index('ix_customer_invoices_customer_id', 'customer_invoices', ['customer_id'])
    op.create_index('ix_customer_invoices_status', 'customer_invoices', ['status'])

    op.create_table(
        'customer_invoice_lines',
        sqa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sqa.Column('invoice_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('customer_invoices.id', ondelete='CASCADE'), nullable=False),
        sqa.Column('product_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('products.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('account_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('chart_of_accounts.id', ondelete='RESTRICT'), nullable=False),
        sqa.Column('description', sqa.String(255), nullable=False),
        sqa.Column('quantity', sqa.Numeric(14, 4), nullable=False, server_default='1.0000'),
        sqa.Column('unit_price', sqa.Numeric(18, 4), nullable=False, server_default='0.0000'),
        sqa.Column('subtotal', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('tax_rate_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('tax_rates.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('tax_amount', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('total_amount', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('created_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
        sqa.Column('updated_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
    )
    op.create_index('ix_customer_invoice_lines_invoice_id', 'customer_invoice_lines', ['invoice_id'])

    op.create_table(
        'customer_credit_notes',
        sqa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sqa.Column('note_number', sqa.String(50), nullable=False, unique=True),
        sqa.Column('customer_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('customers.id', ondelete='RESTRICT'), nullable=False),
        sqa.Column('invoice_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('customer_invoices.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('journal_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('journals.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('issue_date', sqa.Date(), nullable=False),
        sqa.Column('amount', sqa.Numeric(18, 2), nullable=False),
        sqa.Column('reason', sqa.String(255), nullable=False),
        sqa.Column('status', sqa.String(20), nullable=False, server_default='Draft'),
        sqa.Column('created_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
        sqa.Column('updated_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
    )

    op.create_table(
        'customer_debit_notes',
        sqa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sqa.Column('note_number', sqa.String(50), nullable=False, unique=True),
        sqa.Column('customer_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('customers.id', ondelete='RESTRICT'), nullable=False),
        sqa.Column('invoice_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('customer_invoices.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('journal_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('journals.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('issue_date', sqa.Date(), nullable=False),
        sqa.Column('amount', sqa.Numeric(18, 2), nullable=False),
        sqa.Column('reason', sqa.String(255), nullable=False),
        sqa.Column('status', sqa.String(20), nullable=False, server_default='Draft'),
        sqa.Column('created_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
        sqa.Column('updated_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
    )

    op.create_table(
        'customer_ledger_entries',
        sqa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sqa.Column('customer_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False),
        sqa.Column('posting_date', sqa.Date(), nullable=False),
        sqa.Column('document_type', sqa.String(30), nullable=False),
        sqa.Column('document_number', sqa.String(50), nullable=False),
        sqa.Column('journal_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('journals.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('debit', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('credit', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('running_balance', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('description', sqa.String(255), nullable=True),
        sqa.Column('created_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
        sqa.Column('updated_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
    )
    op.create_index('ix_customer_ledger_customer_id', 'customer_ledger_entries', ['customer_id'])

    # 2. Accounts Payable & Supplier Ledger
    op.create_table(
        'supplier_bills',
        sqa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sqa.Column('bill_number', sqa.String(50), nullable=False, unique=True),
        sqa.Column('vendor_bill_number', sqa.String(50), nullable=True),
        sqa.Column('supplier_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('suppliers.id', ondelete='RESTRICT'), nullable=False),
        sqa.Column('purchase_order_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('purchase_orders.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('journal_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('journals.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('bill_date', sqa.Date(), nullable=False),
        sqa.Column('due_date', sqa.Date(), nullable=False),
        sqa.Column('currency_code', sqa.String(10), nullable=False, server_default='USD'),
        sqa.Column('exchange_rate', sqa.Numeric(18, 6), nullable=False, server_default='1.000000'),
        sqa.Column('subtotal', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('tax_amount', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('total_amount', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('paid_amount', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('outstanding_amount', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('status', sqa.String(20), nullable=False, server_default='Draft'),
        sqa.Column('notes', sqa.Text(), nullable=True),
        sqa.Column('created_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
        sqa.Column('updated_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
    )
    op.create_index('ix_supplier_bills_bill_number', 'supplier_bills', ['bill_number'])
    op.create_index('ix_supplier_bills_supplier_id', 'supplier_bills', ['supplier_id'])

    op.create_table(
        'supplier_bill_lines',
        sqa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sqa.Column('bill_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('supplier_bills.id', ondelete='CASCADE'), nullable=False),
        sqa.Column('product_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('products.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('account_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('chart_of_accounts.id', ondelete='RESTRICT'), nullable=False),
        sqa.Column('description', sqa.String(255), nullable=False),
        sqa.Column('quantity', sqa.Numeric(14, 4), nullable=False, server_default='1.0000'),
        sqa.Column('unit_price', sqa.Numeric(18, 4), nullable=False, server_default='0.0000'),
        sqa.Column('subtotal', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('tax_rate_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('tax_rates.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('tax_amount', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('total_amount', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('created_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
        sqa.Column('updated_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
    )

    op.create_table(
        'supplier_credit_notes',
        sqa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sqa.Column('note_number', sqa.String(50), nullable=False, unique=True),
        sqa.Column('supplier_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('suppliers.id', ondelete='RESTRICT'), nullable=False),
        sqa.Column('bill_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('supplier_bills.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('journal_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('journals.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('issue_date', sqa.Date(), nullable=False),
        sqa.Column('amount', sqa.Numeric(18, 2), nullable=False),
        sqa.Column('reason', sqa.String(255), nullable=False),
        sqa.Column('status', sqa.String(20), nullable=False, server_default='Draft'),
        sqa.Column('created_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
        sqa.Column('updated_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
    )

    op.create_table(
        'supplier_debit_notes',
        sqa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sqa.Column('note_number', sqa.String(50), nullable=False, unique=True),
        sqa.Column('supplier_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('suppliers.id', ondelete='RESTRICT'), nullable=False),
        sqa.Column('bill_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('supplier_bills.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('journal_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('journals.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('issue_date', sqa.Date(), nullable=False),
        sqa.Column('amount', sqa.Numeric(18, 2), nullable=False),
        sqa.Column('reason', sqa.String(255), nullable=False),
        sqa.Column('status', sqa.String(20), nullable=False, server_default='Draft'),
        sqa.Column('created_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
        sqa.Column('updated_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
    )

    op.create_table(
        'supplier_ledger_entries',
        sqa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sqa.Column('supplier_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('suppliers.id', ondelete='CASCADE'), nullable=False),
        sqa.Column('posting_date', sqa.Date(), nullable=False),
        sqa.Column('document_type', sqa.String(30), nullable=False),
        sqa.Column('document_number', sqa.String(50), nullable=False),
        sqa.Column('journal_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('journals.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('debit', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('credit', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('running_balance', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('description', sqa.String(255), nullable=True),
        sqa.Column('created_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
        sqa.Column('updated_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
    )
    op.create_index('ix_supplier_ledger_supplier_id', 'supplier_ledger_entries', ['supplier_id'])

    # 3. Bank Management
    op.create_table(
        'bank_accounts',
        sqa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sqa.Column('account_name', sqa.String(100), nullable=False),
        sqa.Column('account_number', sqa.String(50), nullable=False, unique=True),
        sqa.Column('bank_name', sqa.String(100), nullable=False),
        sqa.Column('branch_name', sqa.String(100), nullable=True),
        sqa.Column('swift_code', sqa.String(20), nullable=True),
        sqa.Column('iban', sqa.String(50), nullable=True),
        sqa.Column('currency_code', sqa.String(10), nullable=False, server_default='USD'),
        sqa.Column('gl_account_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('chart_of_accounts.id', ondelete='RESTRICT'), nullable=False),
        sqa.Column('current_balance', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('is_active', sqa.Boolean(), nullable=False, server_default='true'),
        sqa.Column('created_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
        sqa.Column('updated_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
    )

    # 4. Payments & Payment Allocations
    op.create_table(
        'receipt_vouchers',
        sqa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sqa.Column('voucher_number', sqa.String(50), nullable=False, unique=True),
        sqa.Column('customer_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('customers.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('payment_mode', sqa.String(20), nullable=False),
        sqa.Column('bank_account_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('bank_accounts.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('cash_account_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('chart_of_accounts.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('journal_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('journals.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('receipt_date', sqa.Date(), nullable=False),
        sqa.Column('amount', sqa.Numeric(18, 2), nullable=False),
        sqa.Column('allocated_amount', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('unallocated_amount', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('reference_number', sqa.String(100), nullable=True),
        sqa.Column('status', sqa.String(20), nullable=False, server_default='Draft'),
        sqa.Column('notes', sqa.Text(), nullable=True),
        sqa.Column('created_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
        sqa.Column('updated_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
    )

    op.create_table(
        'payment_vouchers',
        sqa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sqa.Column('voucher_number', sqa.String(50), nullable=False, unique=True),
        sqa.Column('supplier_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('suppliers.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('payment_mode', sqa.String(20), nullable=False),
        sqa.Column('bank_account_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('bank_accounts.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('cash_account_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('chart_of_accounts.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('journal_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('journals.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('payment_date', sqa.Date(), nullable=False),
        sqa.Column('amount', sqa.Numeric(18, 2), nullable=False),
        sqa.Column('allocated_amount', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('unallocated_amount', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('reference_number', sqa.String(100), nullable=True),
        sqa.Column('status', sqa.String(20), nullable=False, server_default='Draft'),
        sqa.Column('notes', sqa.Text(), nullable=True),
        sqa.Column('created_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
        sqa.Column('updated_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
    )

    op.create_table(
        'payment_allocations',
        sqa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sqa.Column('receipt_voucher_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('receipt_vouchers.id', ondelete='CASCADE'), nullable=True),
        sqa.Column('payment_voucher_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('payment_vouchers.id', ondelete='CASCADE'), nullable=True),
        sqa.Column('customer_invoice_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('customer_invoices.id', ondelete='CASCADE'), nullable=True),
        sqa.Column('supplier_bill_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('supplier_bills.id', ondelete='CASCADE'), nullable=True),
        sqa.Column('allocation_amount', sqa.Numeric(18, 2), nullable=False),
        sqa.Column('allocation_date', sqa.Date(), nullable=False),
        sqa.Column('created_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
        sqa.Column('updated_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
    )

    # 5. Bank Transactions & Statements & Reconciliation
    op.create_table(
        'bank_transactions',
        sqa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sqa.Column('bank_account_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('bank_accounts.id', ondelete='CASCADE'), nullable=False),
        sqa.Column('transaction_date', sqa.Date(), nullable=False),
        sqa.Column('transaction_type', sqa.String(20), nullable=False),
        sqa.Column('amount', sqa.Numeric(18, 2), nullable=False),
        sqa.Column('reference_number', sqa.String(100), nullable=True),
        sqa.Column('payee_or_payer', sqa.String(150), nullable=True),
        sqa.Column('description', sqa.String(255), nullable=True),
        sqa.Column('journal_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('journals.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('is_reconciled', sqa.Boolean(), nullable=False, server_default='false'),
        sqa.Column('created_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
        sqa.Column('updated_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
    )

    op.create_table(
        'bank_statements',
        sqa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sqa.Column('bank_account_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('bank_accounts.id', ondelete='CASCADE'), nullable=False),
        sqa.Column('statement_number', sqa.String(50), nullable=False),
        sqa.Column('start_date', sqa.Date(), nullable=False),
        sqa.Column('end_date', sqa.Date(), nullable=False),
        sqa.Column('opening_balance', sqa.Numeric(18, 2), nullable=False),
        sqa.Column('closing_balance', sqa.Numeric(18, 2), nullable=False),
        sqa.Column('status', sqa.String(20), nullable=False, server_default='Uploaded'),
        sqa.Column('created_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
        sqa.Column('updated_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
    )

    op.create_table(
        'bank_statement_lines',
        sqa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sqa.Column('statement_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('bank_statements.id', ondelete='CASCADE'), nullable=False),
        sqa.Column('transaction_date', sqa.Date(), nullable=False),
        sqa.Column('amount', sqa.Numeric(18, 2), nullable=False),
        sqa.Column('reference_number', sqa.String(100), nullable=True),
        sqa.Column('description', sqa.String(255), nullable=True),
        sqa.Column('is_matched', sqa.Boolean(), nullable=False, server_default='false'),
        sqa.Column('matched_transaction_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('bank_transactions.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('created_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
        sqa.Column('updated_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
    )

    op.create_table(
        'bank_reconciliations',
        sqa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sqa.Column('bank_account_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('bank_accounts.id', ondelete='CASCADE'), nullable=False),
        sqa.Column('reconciliation_date', sqa.Date(), nullable=False),
        sqa.Column('statement_balance', sqa.Numeric(18, 2), nullable=False),
        sqa.Column('gl_balance', sqa.Numeric(18, 2), nullable=False),
        sqa.Column('unreconciled_amount', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('status', sqa.String(20), nullable=False, server_default='Draft'),
        sqa.Column('created_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
        sqa.Column('updated_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
    )

    op.create_table(
        'bank_reconciliation_items',
        sqa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sqa.Column('reconciliation_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('bank_reconciliations.id', ondelete='CASCADE'), nullable=False),
        sqa.Column('statement_line_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('bank_statement_lines.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('bank_transaction_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('bank_transactions.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('match_status', sqa.String(20), nullable=False, server_default='Matched'),
        sqa.Column('created_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
        sqa.Column('updated_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
    )

    # 6. Fixed Assets & Depreciation
    op.create_table(
        'asset_categories',
        sqa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sqa.Column('code', sqa.String(50), nullable=False, unique=True),
        sqa.Column('name', sqa.String(100), nullable=False),
        sqa.Column('depreciation_method', sqa.String(30), nullable=False, server_default='StraightLine'),
        sqa.Column('useful_life_years', sqa.Integer(), nullable=False, server_default='5'),
        sqa.Column('asset_account_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('chart_of_accounts.id', ondelete='RESTRICT'), nullable=False),
        sqa.Column('accumulated_depreciation_account_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('chart_of_accounts.id', ondelete='RESTRICT'), nullable=False),
        sqa.Column('depreciation_expense_account_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('chart_of_accounts.id', ondelete='RESTRICT'), nullable=False),
        sqa.Column('created_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
        sqa.Column('updated_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
    )

    op.create_table(
        'fixed_assets',
        sqa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sqa.Column('asset_code', sqa.String(50), nullable=False, unique=True),
        sqa.Column('name', sqa.String(150), nullable=False),
        sqa.Column('category_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('asset_categories.id', ondelete='RESTRICT'), nullable=False),
        sqa.Column('department_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('departments.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('acquisition_date', sqa.Date(), nullable=False),
        sqa.Column('purchase_cost', sqa.Numeric(18, 2), nullable=False),
        sqa.Column('salvage_value', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('current_book_value', sqa.Numeric(18, 2), nullable=False),
        sqa.Column('status', sqa.String(20), nullable=False, server_default='Active'),
        sqa.Column('created_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
        sqa.Column('updated_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
    )

    op.create_table(
        'depreciation_schedules',
        sqa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sqa.Column('asset_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('fixed_assets.id', ondelete='CASCADE'), nullable=False),
        sqa.Column('schedule_date', sqa.Date(), nullable=False),
        sqa.Column('period_name', sqa.String(20), nullable=False),
        sqa.Column('depreciation_amount', sqa.Numeric(18, 2), nullable=False),
        sqa.Column('accumulated_depreciation', sqa.Numeric(18, 2), nullable=False),
        sqa.Column('ending_book_value', sqa.Numeric(18, 2), nullable=False),
        sqa.Column('status', sqa.String(20), nullable=False, server_default='Scheduled'),
        sqa.Column('journal_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('journals.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('created_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
        sqa.Column('updated_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
    )

    # 7. Budgets
    op.create_table(
        'budgets',
        sqa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sqa.Column('code', sqa.String(50), nullable=False, unique=True),
        sqa.Column('name', sqa.String(100), nullable=False),
        sqa.Column('fiscal_year_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('fiscal_years.id', ondelete='CASCADE'), nullable=False),
        sqa.Column('department_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('departments.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('cost_center_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('cost_centers.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('total_budgeted_amount', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('total_actual_amount', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('status', sqa.String(20), nullable=False, server_default='Draft'),
        sqa.Column('created_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
        sqa.Column('updated_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
    )

    op.create_table(
        'budget_lines',
        sqa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sqa.Column('budget_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('budgets.id', ondelete='CASCADE'), nullable=False),
        sqa.Column('account_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('chart_of_accounts.id', ondelete='RESTRICT'), nullable=False),
        sqa.Column('budgeted_amount', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('actual_amount', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('variance_amount', sqa.Numeric(18, 2), nullable=False, server_default='0.00'),
        sqa.Column('created_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
        sqa.Column('updated_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
    )

    # 8. Financial Statement Snapshots
    op.create_table(
        'financial_statement_snapshots',
        sqa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sqa.Column('statement_type', sqa.String(50), nullable=False),
        sqa.Column('as_of_date', sqa.Date(), nullable=False),
        sqa.Column('period_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('fiscal_periods.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('data', postgresql.JSONB(), nullable=False),
        sqa.Column('generated_by_id', postgresql.UUID(as_uuid=True), sqa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sqa.Column('created_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
        sqa.Column('updated_at', sqa.DateTime(timezone=True), server_default=sqa.text('now()'), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('financial_statement_snapshots')
    op.drop_table('budget_lines')
    op.drop_table('budgets')
    op.drop_table('depreciation_schedules')
    op.drop_table('fixed_assets')
    op.drop_table('asset_categories')
    op.drop_table('bank_reconciliation_items')
    op.drop_table('bank_reconciliations')
    op.drop_table('bank_statement_lines')
    op.drop_table('bank_statements')
    op.drop_table('bank_transactions')
    op.drop_table('payment_allocations')
    op.drop_table('payment_vouchers')
    op.drop_table('receipt_vouchers')
    op.drop_table('bank_accounts')
    op.drop_table('supplier_ledger_entries')
    op.drop_table('supplier_debit_notes')
    op.drop_table('supplier_credit_notes')
    op.drop_table('supplier_bill_lines')
    op.drop_table('supplier_bills')
    op.drop_table('customer_ledger_entries')
    op.drop_table('customer_debit_notes')
    op.drop_table('customer_credit_notes')
    op.drop_table('customer_invoice_lines')
    op.drop_table('customer_invoices')
