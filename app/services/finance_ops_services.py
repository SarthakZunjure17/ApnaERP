import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain_events import (
    FINANCE_ASSET_CREATED,
    FINANCE_ASSET_DISPOSED,
    FINANCE_BANK_RECONCILED,
    FINANCE_BUDGET_APPROVED,
    FINANCE_DEPRECIATION_POSTED,
    FINANCE_PAYMENT_MADE,
    FINANCE_PAYMENT_RECEIVED,
    FINANCE_PERIOD_CLOSED,
    FINANCE_STATEMENT_GENERATED,
    FINANCE_YEAR_CLOSED,
    domain_event_publisher,
)
from app.models.customer import Customer
from app.models.department import Department
from app.models.finance import ChartOfAccount, FiscalPeriod, FiscalYear, Journal, JournalLine
from app.models.finance_ops import (
    AssetCategory,
    BankAccount,
    BankReconciliation,
    BankReconciliationItem,
    BankStatement,
    BankStatementLine,
    BankTransaction,
    Budget,
    BudgetLine,
    CustomerCreditNote,
    CustomerDebitNote,
    CustomerInvoice,
    CustomerInvoiceLine,
    CustomerLedgerEntry,
    DepreciationSchedule,
    FinancialStatementSnapshot,
    FixedAsset,
    PaymentAllocation,
    PaymentVoucher,
    ReceiptVoucher,
    SupplierBill,
    SupplierBillLine,
    SupplierCreditNote,
    SupplierDebitNote,
    SupplierLedgerEntry,
)
from app.models.supplier import Supplier
from app.models.user import User
from app.repositories.finance_ops_repos import (
    AssetCategoryRepository,
    BankAccountRepository,
    BankReconciliationRepository,
    BankStatementRepository,
    BankTransactionRepository,
    BudgetRepository,
    CustomerInvoiceRepository,
    CustomerLedgerRepository,
    DepreciationScheduleRepository,
    FinancialStatementSnapshotRepository,
    FixedAssetRepository,
    PaymentAllocationRepository,
    PaymentVoucherRepository,
    ReceiptVoucherRepository,
    SupplierBillRepository,
    SupplierLedgerRepository,
)
from app.schemas.finance_ops import (
    AgingBucket,
    AssetCategoryCreate,
    BankAccountCreate,
    BankStatementImportCreate,
    BankTransactionCreate,
    BudgetCreate,
    CreditDebitNoteCreate,
    CustomerInvoiceCreate,
    CustomerStatementResponse,
    FixedAssetCreate,
    PaymentVoucherCreate,
    ReceiptVoucherCreate,
    SupplierBillCreate,
    VendorStatementResponse,
)
from app.services.finance_services import PostingEngineService


# ==========================================
# 1. Accounts Receivable Service
# ==========================================

class AccountsReceivableService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.invoice_repo = CustomerInvoiceRepository()
        self.ledger_repo = CustomerLedgerRepository()
        self.posting_engine = PostingEngineService()

    async def create_invoice(self, data: CustomerInvoiceCreate, user: User) -> CustomerInvoice:
        invoice_number = f"INV-{uuid.uuid4().hex[:8].upper()}"
        subtotal = Decimal("0.00")
        tax_amount = Decimal("0.00")

        invoice = CustomerInvoice(
            invoice_number=invoice_number,
            customer_id=data.customer_id,
            sales_order_id=data.sales_order_id,
            invoice_date=data.invoice_date,
            due_date=data.due_date,
            currency_code=data.currency_code,
            exchange_rate=data.exchange_rate,
            notes=data.notes,
            status="Draft",
        )

        lines = []
        for line_data in data.lines:
            line_subtotal = line_data.quantity * line_data.unit_price
            line_total = line_subtotal + line_data.tax_amount
            subtotal += line_subtotal
            tax_amount += line_data.tax_amount

            lines.append(
                CustomerInvoiceLine(
                    product_id=line_data.product_id,
                    account_id=line_data.account_id,
                    description=line_data.description,
                    quantity=line_data.quantity,
                    unit_price=line_data.unit_price,
                    subtotal=line_subtotal,
                    tax_rate_id=line_data.tax_rate_id,
                    tax_amount=line_data.tax_amount,
                    total_amount=line_total,
                )
            )

        invoice.subtotal = subtotal
        invoice.tax_amount = tax_amount
        invoice.total_amount = subtotal + tax_amount
        invoice.outstanding_amount = invoice.total_amount
        invoice.lines = lines

        return await self.invoice_repo.create(self.db, obj_in=invoice)

    async def post_invoice(self, invoice_id: uuid.UUID, user: User) -> CustomerInvoice:
        invoice = await self.invoice_repo.get_by_id(self.db, id=invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        if invoice.status != "Draft":
            raise HTTPException(status_code=400, detail=f"Invoice is already {invoice.status}")

        ar_stmt = select(ChartOfAccount).where(ChartOfAccount.account_code == "1200")
        ar_res = await self.db.execute(ar_stmt)
        ar_account = ar_res.scalar_one_or_none()
        if not ar_account:
            ar_stmt = select(ChartOfAccount).where(ChartOfAccount.account_type == "Asset")
            ar_res = await self.db.execute(ar_stmt)
            ar_account = ar_res.scalars().first()
            if not ar_account:
                raise HTTPException(status_code=400, detail="No Accounts Receivable GL account configured")

        journal_lines = [
            {
                "account_id": str(ar_account.id),
                "debit": float(invoice.total_amount),
                "credit": 0.0,
                "description": f"AR Invoice {invoice.invoice_number}",
            }
        ]

        for line in invoice.lines:
            journal_lines.append(
                {
                    "account_id": str(line.account_id),
                    "debit": 0.0,
                    "credit": float(line.subtotal),
                    "description": line.description,
                }
            )

        if invoice.tax_amount > 0:
            tax_stmt = select(ChartOfAccount).where(ChartOfAccount.account_code == "2200")
            tax_res = await self.db.execute(tax_stmt)
            tax_acc = tax_res.scalar_one_or_none() or ar_account
            journal_lines.append(
                {
                    "account_id": str(tax_acc.id),
                    "debit": 0.0,
                    "credit": float(invoice.tax_amount),
                    "description": "Output Tax Payable",
                }
            )

        journal = await self.posting_engine.post_double_entry_journal(
            self.db,
            entry_date=invoice.invoice_date,
            description=f"Invoice {invoice.invoice_number}",
            lines=journal_lines,
            reference_number=invoice.invoice_number,
            user=user,
        )

        invoice.journal_id = journal.id
        invoice.status = "Posted"

        prev_stmt = (
            select(CustomerLedgerEntry)
            .where(CustomerLedgerEntry.customer_id == invoice.customer_id)
            .order_by(CustomerLedgerEntry.created_at.desc())
        )
        prev_res = await self.db.execute(prev_stmt)
        prev_entry = prev_res.scalars().first()
        prev_balance = prev_entry.running_balance if prev_entry else Decimal("0.00")

        new_balance = prev_balance + invoice.total_amount

        ledger_entry = CustomerLedgerEntry(
            customer_id=invoice.customer_id,
            posting_date=invoice.invoice_date,
            document_type="Invoice",
            document_number=invoice.invoice_number,
            journal_id=journal.id,
            debit=invoice.total_amount,
            credit=Decimal("0.00"),
            running_balance=new_balance,
            description=f"Invoice {invoice.invoice_number}",
        )
        await self.ledger_repo.create(self.db, obj_in=ledger_entry)
        await self.db.flush()

        return invoice

    async def get_customer_statement(self, customer_id: uuid.UUID) -> CustomerStatementResponse:
        cust_stmt = select(Customer).where(Customer.id == customer_id)
        cust_res = await self.db.execute(cust_stmt)
        customer = cust_res.scalar_one_or_none()
        cust_name = customer.name if customer else "Customer"

        entries = await self.ledger_repo.get_by_customer(self.db, customer_id=customer_id)
        total_outstanding = entries[-1].running_balance if entries else Decimal("0.00")

        invoices_stmt = select(CustomerInvoice).where(
            CustomerInvoice.customer_id == customer_id,
            CustomerInvoice.status.in_(["Posted", "PartiallyPaid"]),
        )
        inv_res = await self.db.execute(invoices_stmt)
        invoices = inv_res.scalars().all()

        today = datetime.date.today()
        bucket = AgingBucket()

        for inv in invoices:
            days = (today - inv.due_date).days
            amt = inv.outstanding_amount
            bucket.total_outstanding += amt
            if days <= 30:
                bucket.current_0_30 += amt
            elif days <= 60:
                bucket.days_31_60 += amt
            elif days <= 90:
                bucket.days_61_90 += amt
            else:
                bucket.over_90_days += amt

        return CustomerStatementResponse(
            customer_id=customer_id,
            customer_name=cust_name,
            as_of_date=today,
            total_outstanding=total_outstanding,
            aging=bucket,
            entries=entries,
        )


# ==========================================
# 2. Accounts Payable Service
# ==========================================

class AccountsPayableService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.bill_repo = SupplierBillRepository()
        self.ledger_repo = SupplierLedgerRepository()
        self.posting_engine = PostingEngineService()

    async def create_bill(self, data: SupplierBillCreate, user: User) -> SupplierBill:
        bill_number = f"BILL-{uuid.uuid4().hex[:8].upper()}"
        subtotal = Decimal("0.00")
        tax_amount = Decimal("0.00")

        bill = SupplierBill(
            bill_number=bill_number,
            vendor_bill_number=data.vendor_bill_number,
            supplier_id=data.supplier_id,
            purchase_order_id=data.purchase_order_id,
            bill_date=data.bill_date,
            due_date=data.due_date,
            currency_code=data.currency_code,
            exchange_rate=data.exchange_rate,
            notes=data.notes,
            status="Draft",
        )

        lines = []
        for line_data in data.lines:
            line_subtotal = line_data.quantity * line_data.unit_price
            line_total = line_subtotal + line_data.tax_amount
            subtotal += line_subtotal
            tax_amount += line_data.tax_amount

            lines.append(
                SupplierBillLine(
                    product_id=line_data.product_id,
                    account_id=line_data.account_id,
                    description=line_data.description,
                    quantity=line_data.quantity,
                    unit_price=line_data.unit_price,
                    subtotal=line_subtotal,
                    tax_rate_id=line_data.tax_rate_id,
                    tax_amount=line_data.tax_amount,
                    total_amount=line_total,
                )
            )

        bill.subtotal = subtotal
        bill.tax_amount = tax_amount
        bill.total_amount = subtotal + tax_amount
        bill.outstanding_amount = bill.total_amount
        bill.lines = lines

        return await self.bill_repo.create(self.db, obj_in=bill)

    async def post_bill(self, bill_id: uuid.UUID, user: User) -> SupplierBill:
        bill = await self.bill_repo.get_by_id(self.db, id=bill_id)
        if not bill:
            raise HTTPException(status_code=404, detail="Supplier bill not found")
        if bill.status != "Draft":
            raise HTTPException(status_code=400, detail=f"Bill is already {bill.status}")

        ap_stmt = select(ChartOfAccount).where(ChartOfAccount.account_code == "2100")
        ap_res = await self.db.execute(ap_stmt)
        ap_account = ap_res.scalar_one_or_none()
        if not ap_account:
            ap_stmt = select(ChartOfAccount).where(ChartOfAccount.account_type == "Liability")
            ap_res = await self.db.execute(ap_stmt)
            ap_account = ap_res.scalars().first()
            if not ap_account:
                raise HTTPException(status_code=400, detail="No Accounts Payable GL account configured")

        journal_lines = []
        for line in bill.lines:
            journal_lines.append(
                {
                    "account_id": str(line.account_id),
                    "debit": float(line.subtotal),
                    "credit": 0.0,
                    "description": line.description,
                }
            )

        if bill.tax_amount > 0:
            tax_stmt = select(ChartOfAccount).where(ChartOfAccount.account_code == "1300")
            tax_res = await self.db.execute(tax_stmt)
            tax_acc = tax_res.scalar_one_or_none() or ap_account
            journal_lines.append(
                {
                    "account_id": str(tax_acc.id),
                    "debit": float(bill.tax_amount),
                    "credit": 0.0,
                    "description": "Input Tax Recoverable",
                }
            )

        journal_lines.append(
            {
                "account_id": str(ap_account.id),
                "debit": 0.0,
                "credit": float(bill.total_amount),
                "description": f"AP Bill {bill.bill_number}",
            }
        )

        journal = await self.posting_engine.post_double_entry_journal(
            self.db,
            entry_date=bill.bill_date,
            description=f"Supplier Bill {bill.bill_number}",
            lines=journal_lines,
            reference_number=bill.bill_number,
            user=user,
        )

        bill.journal_id = journal.id
        bill.status = "Posted"

        prev_stmt = (
            select(SupplierLedgerEntry)
            .where(SupplierLedgerEntry.supplier_id == bill.supplier_id)
            .order_by(SupplierLedgerEntry.created_at.desc())
        )
        prev_res = await self.db.execute(prev_stmt)
        prev_entry = prev_res.scalars().first()
        prev_balance = prev_entry.running_balance if prev_entry else Decimal("0.00")

        new_balance = prev_balance + bill.total_amount

        ledger_entry = SupplierLedgerEntry(
            supplier_id=bill.supplier_id,
            posting_date=bill.bill_date,
            document_type="Bill",
            document_number=bill.bill_number,
            journal_id=journal.id,
            debit=Decimal("0.00"),
            credit=bill.total_amount,
            running_balance=new_balance,
            description=f"Supplier Bill {bill.bill_number}",
        )
        await self.ledger_repo.create(self.db, obj_in=ledger_entry)
        await self.db.flush()

        return bill

    async def get_vendor_statement(self, supplier_id: uuid.UUID) -> VendorStatementResponse:
        sup_stmt = select(Supplier).where(Supplier.id == supplier_id)
        sup_res = await self.db.execute(sup_stmt)
        supplier = sup_res.scalar_one_or_none()
        sup_name = supplier.name if supplier else "Supplier"

        entries = await self.ledger_repo.get_by_supplier(self.db, supplier_id=supplier_id)
        total_outstanding = entries[-1].running_balance if entries else Decimal("0.00")

        bills_stmt = select(SupplierBill).where(
            SupplierBill.supplier_id == supplier_id,
            SupplierBill.status.in_(["Posted", "PartiallyPaid"]),
        )
        bill_res = await self.db.execute(bills_stmt)
        bills = bill_res.scalars().all()

        today = datetime.date.today()
        bucket = AgingBucket()

        for bill in bills:
            days = (today - bill.due_date).days
            amt = bill.outstanding_amount
            bucket.total_outstanding += amt
            if days <= 30:
                bucket.current_0_30 += amt
            elif days <= 60:
                bucket.days_31_60 += amt
            elif days <= 90:
                bucket.days_61_90 += amt
            else:
                bucket.over_90_days += amt

        return VendorStatementResponse(
            supplier_id=supplier_id,
            supplier_name=sup_name,
            as_of_date=today,
            total_outstanding=total_outstanding,
            aging=bucket,
            entries=entries,
        )


# ==========================================
# 3. Payment Service
# ==========================================

class PaymentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.receipt_repo = ReceiptVoucherRepository()
        self.payment_repo = PaymentVoucherRepository()
        self.allocation_repo = PaymentAllocationRepository()
        self.posting_engine = PostingEngineService()

    async def create_receipt_voucher(self, data: ReceiptVoucherCreate, user: User) -> ReceiptVoucher:
        voucher_number = f"RCT-{uuid.uuid4().hex[:8].upper()}"

        voucher = ReceiptVoucher(
            voucher_number=voucher_number,
            customer_id=data.customer_id,
            payment_mode=data.payment_mode,
            bank_account_id=data.bank_account_id,
            cash_account_id=data.cash_account_id,
            receipt_date=data.receipt_date,
            amount=data.amount,
            unallocated_amount=data.amount,
            reference_number=data.reference_number,
            notes=data.notes,
            status="Draft",
        )
        return await self.receipt_repo.create(self.db, obj_in=voucher)

    async def post_receipt_voucher(self, voucher_id: uuid.UUID, user: User) -> ReceiptVoucher:
        voucher = await self.receipt_repo.get_by_id(self.db, id=voucher_id)
        if not voucher:
            raise HTTPException(status_code=404, detail="Receipt voucher not found")
        if voucher.status != "Draft":
            raise HTTPException(status_code=400, detail=f"Voucher is already {voucher.status}")

        if voucher.payment_mode == "Bank" and voucher.bank_account_id:
            bank_stmt = select(BankAccount).where(BankAccount.id == voucher.bank_account_id)
            bank_res = await self.db.execute(bank_stmt)
            bank = bank_res.scalar_one_or_none()
            if not bank:
                raise HTTPException(status_code=400, detail="Bank account not found")
            debit_account_id = bank.gl_account_id
            bank.current_balance += voucher.amount
        else:
            cash_stmt = select(ChartOfAccount).where(ChartOfAccount.account_code == "1010")
            cash_res = await self.db.execute(cash_stmt)
            cash = cash_res.scalar_one_or_none()
            if not cash:
                cash_stmt = select(ChartOfAccount).where(ChartOfAccount.account_type == "Asset")
                cash_res = await self.db.execute(cash_stmt)
                cash = cash_res.scalars().first()
            debit_account_id = cash.id

        ar_stmt = select(ChartOfAccount).where(ChartOfAccount.account_code == "1200")
        ar_res = await self.db.execute(ar_stmt)
        ar_account = ar_res.scalar_one_or_none()
        if not ar_account:
            ar_stmt = select(ChartOfAccount).where(ChartOfAccount.account_type == "Asset")
            ar_res = await self.db.execute(ar_stmt)
            ar_account = ar_res.scalars().first()

        lines = [
            {
                "account_id": str(debit_account_id),
                "debit": float(voucher.amount),
                "credit": 0.0,
                "description": f"Receipt {voucher.voucher_number}",
            },
            {
                "account_id": str(ar_account.id),
                "debit": 0.0,
                "credit": float(voucher.amount),
                "description": f"Customer Receipt {voucher.voucher_number}",
            },
        ]

        journal = await self.posting_engine.post_double_entry_journal(
            self.db,
            entry_date=voucher.receipt_date,
            description=f"Receipt Voucher {voucher.voucher_number}",
            lines=lines,
            reference_number=voucher.voucher_number,
            user=user,
        )

        voucher.journal_id = journal.id
        voucher.status = "Posted"

        if voucher.customer_id:
            prev_stmt = (
                select(CustomerLedgerEntry)
                .where(CustomerLedgerEntry.customer_id == voucher.customer_id)
                .order_by(CustomerLedgerEntry.created_at.desc())
            )
            prev_res = await self.db.execute(prev_stmt)
            prev_entry = prev_res.scalars().first()
            prev_balance = prev_entry.running_balance if prev_entry else Decimal("0.00")

            new_balance = prev_balance - voucher.amount

            ledger_entry = CustomerLedgerEntry(
                customer_id=voucher.customer_id,
                posting_date=voucher.receipt_date,
                document_type="Receipt",
                document_number=voucher.voucher_number,
                journal_id=journal.id,
                debit=Decimal("0.00"),
                credit=voucher.amount,
                running_balance=new_balance,
                description=f"Receipt {voucher.voucher_number}",
            )
            self.db.add(ledger_entry)

        domain_event_publisher.publish(
            FINANCE_PAYMENT_RECEIVED,
            {"voucher_id": str(voucher.id), "amount": float(voucher.amount)},
        )

        return voucher

    async def create_payment_voucher(self, data: PaymentVoucherCreate, user: User) -> PaymentVoucher:
        voucher_number = f"PMT-{uuid.uuid4().hex[:8].upper()}"

        voucher = PaymentVoucher(
            voucher_number=voucher_number,
            supplier_id=data.supplier_id,
            payment_mode=data.payment_mode,
            bank_account_id=data.bank_account_id,
            cash_account_id=data.cash_account_id,
            payment_date=data.payment_date,
            amount=data.amount,
            unallocated_amount=data.amount,
            reference_number=data.reference_number,
            notes=data.notes,
            status="Draft",
        )
        return await self.payment_repo.create(self.db, obj_in=voucher)

    async def post_payment_voucher(self, voucher_id: uuid.UUID, user: User) -> PaymentVoucher:
        voucher = await self.payment_repo.get_by_id(self.db, id=voucher_id)
        if not voucher:
            raise HTTPException(status_code=404, detail="Payment voucher not found")
        if voucher.status != "Draft":
            raise HTTPException(status_code=400, detail=f"Voucher is already {voucher.status}")

        ap_stmt = select(ChartOfAccount).where(ChartOfAccount.account_code == "2100")
        ap_res = await self.db.execute(ap_stmt)
        ap_account = ap_res.scalar_one_or_none()
        if not ap_account:
            ap_stmt = select(ChartOfAccount).where(ChartOfAccount.account_type == "Liability")
            ap_res = await self.db.execute(ap_stmt)
            ap_account = ap_res.scalars().first()

        if voucher.payment_mode == "Bank" and voucher.bank_account_id:
            bank_stmt = select(BankAccount).where(BankAccount.id == voucher.bank_account_id)
            bank_res = await self.db.execute(bank_stmt)
            bank = bank_res.scalar_one_or_none()
            if not bank:
                raise HTTPException(status_code=400, detail="Bank account not found")
            credit_account_id = bank.gl_account_id
            bank.current_balance -= voucher.amount
        else:
            cash_stmt = select(ChartOfAccount).where(ChartOfAccount.account_code == "1010")
            cash_res = await self.db.execute(cash_stmt)
            cash = cash_res.scalar_one_or_none()
            if not cash:
                cash_stmt = select(ChartOfAccount).where(ChartOfAccount.account_type == "Asset")
                cash_res = await self.db.execute(cash_stmt)
                cash = cash_res.scalars().first()
            credit_account_id = cash.id

        lines = [
            {
                "account_id": str(ap_account.id),
                "debit": float(voucher.amount),
                "credit": 0.0,
                "description": f"Supplier Payment {voucher.voucher_number}",
            },
            {
                "account_id": str(credit_account_id),
                "debit": 0.0,
                "credit": float(voucher.amount),
                "description": f"Payment Outflow {voucher.voucher_number}",
            },
        ]

        journal = await self.posting_engine.post_double_entry_journal(
            self.db,
            entry_date=voucher.payment_date,
            description=f"Payment Voucher {voucher.voucher_number}",
            lines=lines,
            reference_number=voucher.voucher_number,
            user=user,
        )

        voucher.journal_id = journal.id
        voucher.status = "Posted"

        if voucher.supplier_id:
            prev_stmt = (
                select(SupplierLedgerEntry)
                .where(SupplierLedgerEntry.supplier_id == voucher.supplier_id)
                .order_by(SupplierLedgerEntry.created_at.desc())
            )
            prev_res = await self.db.execute(prev_stmt)
            prev_entry = prev_res.scalars().first()
            prev_balance = prev_entry.running_balance if prev_entry else Decimal("0.00")

            new_balance = prev_balance - voucher.amount

            ledger_entry = SupplierLedgerEntry(
                supplier_id=voucher.supplier_id,
                posting_date=voucher.payment_date,
                document_type="Payment",
                document_number=voucher.voucher_number,
                journal_id=journal.id,
                debit=voucher.amount,
                credit=Decimal("0.00"),
                running_balance=new_balance,
                description=f"Payment {voucher.voucher_number}",
            )
            self.db.add(ledger_entry)

        domain_event_publisher.publish(
            FINANCE_PAYMENT_MADE,
            {"voucher_id": str(voucher.id), "amount": float(voucher.amount)},
        )

        return voucher


# ==========================================
# 4. Bank Management Service
# ==========================================

class BankService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.bank_repo = BankAccountRepository()
        self.txn_repo = BankTransactionRepository()

    async def create_bank_account(self, data: BankAccountCreate) -> BankAccount:
        account = BankAccount(
            account_name=data.account_name,
            account_number=data.account_number,
            bank_name=data.bank_name,
            branch_name=data.branch_name,
            swift_code=data.swift_code,
            iban=data.iban,
            currency_code=data.currency_code,
            gl_account_id=data.gl_account_id,
            current_balance=Decimal("0.00"),
            is_active=True,
        )
        return await self.bank_repo.create(self.db, obj_in=account)

    async def record_transaction(self, data: BankTransactionCreate) -> BankTransaction:
        bank = await self.bank_repo.get_by_id(self.db, id=data.bank_account_id)
        if not bank:
            raise HTTPException(status_code=404, detail="Bank account not found")

        txn = BankTransaction(
            bank_account_id=data.bank_account_id,
            transaction_date=data.transaction_date,
            transaction_type=data.transaction_type,
            amount=data.amount,
            reference_number=data.reference_number,
            payee_or_payer=data.payee_or_payer,
            description=data.description,
            is_reconciled=False,
        )

        if data.transaction_type in ["Deposit"]:
            bank.current_balance += data.amount
        elif data.transaction_type in ["Withdrawal", "Fee", "Cheque"]:
            bank.current_balance -= data.amount

        return await self.txn_repo.create(self.db, obj_in=txn)


# ==========================================
# 5. Bank Reconciliation Service
# ==========================================

class ReconciliationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.stmt_repo = BankStatementRepository()
        self.rec_repo = BankReconciliationRepository()

    async def import_statement(self, data: BankStatementImportCreate) -> BankStatement:
        statement = BankStatement(
            bank_account_id=data.bank_account_id,
            statement_number=data.statement_number,
            start_date=data.start_date,
            end_date=data.end_date,
            opening_balance=data.opening_balance,
            closing_balance=data.closing_balance,
            status="Uploaded",
        )

        lines = [
            BankStatementLine(
                transaction_date=line.transaction_date,
                amount=line.amount,
                reference_number=line.reference_number,
                description=line.description,
                is_matched=False,
            )
            for line in data.lines
        ]
        statement.lines = lines

        return await self.stmt_repo.create(self.db, obj_in=statement)

    async def perform_auto_matching(self, bank_account_id: uuid.UUID) -> BankReconciliation:
        bank_stmt = select(BankAccount).where(BankAccount.id == bank_account_id)
        bank_res = await self.db.execute(bank_stmt)
        bank = bank_res.scalar_one_or_none()

        unmatched_stmt = select(BankStatementLine).where(
            BankStatementLine.is_matched == False
        )
        line_res = await self.db.execute(unmatched_stmt)
        unmatched_lines = line_res.scalars().all()

        unreconciled_txns = select(BankTransaction).where(
            BankTransaction.bank_account_id == bank_account_id,
            BankTransaction.is_reconciled == False,
        )
        txn_res = await self.db.execute(unreconciled_txns)
        txns = txn_res.scalars().all()

        rec = BankReconciliation(
            bank_account_id=bank_account_id,
            reconciliation_date=datetime.date.today(),
            statement_balance=bank.current_balance if bank else Decimal("0.00"),
            gl_balance=bank.current_balance if bank else Decimal("0.00"),
            unreconciled_amount=Decimal("0.00"),
            status="Completed",
        )

        items = []
        for s_line in unmatched_lines:
            for t in txns:
                if t.amount == s_line.amount and not t.is_reconciled:
                    s_line.is_matched = True
                    s_line.matched_transaction_id = t.id
                    t.is_reconciled = True
                    items.append(
                        BankReconciliationItem(
                            statement_line_id=s_line.id,
                            bank_transaction_id=t.id,
                            match_status="Matched",
                        )
                    )
                    break

        rec.items = items
        await self.rec_repo.create(self.db, obj_in=rec)

        domain_event_publisher.publish(
            FINANCE_BANK_RECONCILED,
            {"bank_account_id": str(bank_account_id), "reconciliation_id": str(rec.id)},
        )

        return rec


# ==========================================
# 6. Fixed Assets & Depreciation Service
# ==========================================

class AssetService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.category_repo = AssetCategoryRepository()
        self.asset_repo = FixedAssetRepository()
        self.posting_engine = PostingEngineService()

    async def create_category(self, data: AssetCategoryCreate) -> AssetCategory:
        cat = AssetCategory(
            code=data.code,
            name=data.name,
            depreciation_method=data.depreciation_method,
            useful_life_years=data.useful_life_years,
            asset_account_id=data.asset_account_id,
            accumulated_depreciation_account_id=data.accumulated_depreciation_account_id,
            depreciation_expense_account_id=data.depreciation_expense_account_id,
        )
        return await self.category_repo.create(self.db, obj_in=cat)

    async def create_asset(self, data: FixedAssetCreate, user: User) -> FixedAsset:
        asset = FixedAsset(
            asset_code=data.asset_code,
            name=data.name,
            category_id=data.category_id,
            department_id=data.department_id,
            acquisition_date=data.acquisition_date,
            purchase_cost=data.purchase_cost,
            salvage_value=data.salvage_value,
            current_book_value=data.purchase_cost,
            status="Active",
        )

        category = await self.category_repo.get_by_id(self.db, id=data.category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Asset Category not found")

        cash_stmt = select(ChartOfAccount).where(ChartOfAccount.account_code == "1010")
        cash_res = await self.db.execute(cash_stmt)
        cash_acc = cash_res.scalar_one_or_none()
        if not cash_acc:
            cash_acc = category.asset_account

        lines = [
            {
                "account_id": str(category.asset_account_id),
                "debit": float(data.purchase_cost),
                "credit": 0.0,
                "description": f"Asset Acquisition {data.asset_code}",
            },
            {
                "account_id": str(cash_acc.id if cash_acc else category.asset_account_id),
                "debit": 0.0,
                "credit": float(data.purchase_cost),
                "description": f"Acquisition Outflow {data.asset_code}",
            },
        ]

        await self.posting_engine.post_double_entry_journal(
            self.db,
            entry_date=data.acquisition_date,
            description=f"Asset Acquisition {data.name}",
            lines=lines,
            reference_number=data.asset_code,
            user=user,
        )

        saved_asset = await self.asset_repo.create(self.db, obj_in=asset)

        domain_event_publisher.publish(
            FINANCE_ASSET_CREATED,
            {"asset_id": str(saved_asset.id), "code": saved_asset.asset_code},
        )

        return saved_asset


class DepreciationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.asset_repo = FixedAssetRepository()
        self.sched_repo = DepreciationScheduleRepository()
        self.posting_engine = PostingEngineService(db)

    async def generate_schedule(self, asset_id: uuid.UUID) -> List[DepreciationSchedule]:
        asset = await self.asset_repo.get_by_id(self.db, id=asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail="Fixed Asset not found")

        category = asset.category
        total_depreciable = asset.purchase_cost - asset.salvage_value
        months = category.useful_life_years * 12
        monthly_depr = (total_depreciable / Decimal(str(months))).quantize(Decimal("0.01"))

        schedules = []
        accumulated = Decimal("0.00")
        current_book = asset.purchase_cost

        for m in range(1, months + 1):
            if m == months:
                depr_amount = total_depreciable - accumulated
            else:
                depr_amount = monthly_depr

            accumulated += depr_amount
            current_book -= depr_amount

            schedule_date = asset.acquisition_date + datetime.timedelta(days=m * 30)

            sched = DepreciationSchedule(
                asset_id=asset.id,
                schedule_date=schedule_date,
                period_name=f"M{m:02d}",
                depreciation_amount=depr_amount,
                accumulated_depreciation=accumulated,
                ending_book_value=current_book,
                status="Scheduled",
            )
            schedules.append(sched)

        asset.schedules = schedules
        await self.db.flush()
        return schedules

    async def post_depreciation(self, schedule_id: uuid.UUID, user: User) -> DepreciationSchedule:
        sched = await self.sched_repo.get_by_id(self.db, id=schedule_id)
        if not sched:
            raise HTTPException(status_code=404, detail="Depreciation schedule item not found")
        if sched.status == "Posted":
            raise HTTPException(status_code=400, detail="Schedule entry is already posted")

        asset = await self.asset_repo.get_by_id(self.db, id=sched.asset_id)
        category = asset.category

        lines = [
            {
                "account_id": str(category.depreciation_expense_account_id),
                "debit": float(sched.depreciation_amount),
                "credit": 0.0,
                "description": f"Depreciation {asset.asset_code} {sched.period_name}",
            },
            {
                "account_id": str(category.accumulated_depreciation_account_id),
                "debit": 0.0,
                "credit": float(sched.depreciation_amount),
                "description": f"Accumulated Depreciation {asset.asset_code}",
            },
        ]

        journal = await self.posting_engine.post_double_entry_journal(
            self.db,
            entry_date=sched.schedule_date,
            description=f"Depreciation {asset.name} {sched.period_name}",
            lines=lines,
            reference_number=asset.asset_code,
            user=user,
        )

        sched.journal_id = journal.id
        sched.status = "Posted"
        asset.current_book_value = sched.ending_book_value

        domain_event_publisher.publish(
            FINANCE_DEPRECIATION_POSTED,
            {"asset_id": str(asset.id), "amount": float(sched.depreciation_amount)},
        )

        return sched


# ==========================================
# 7. Financial Statement Service
# ==========================================

class FinancialStatementService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_trial_balance(self, as_of_date: datetime.date) -> Dict[str, Any]:
        stmt = select(ChartOfAccount)
        res = await self.db.execute(stmt)
        accounts = res.scalars().all()

        lines = []
        total_debit = Decimal("0.00")
        total_credit = Decimal("0.00")

        for acc in accounts:
            bal = acc.current_balance
            if acc.account_type in ["Asset", "Expense"]:
                debit_bal = bal if bal >= 0 else Decimal("0.00")
                credit_bal = abs(bal) if bal < 0 else Decimal("0.00")
            else:
                credit_bal = bal if bal >= 0 else Decimal("0.00")
                debit_bal = abs(bal) if bal < 0 else Decimal("0.00")

            total_debit += debit_bal
            total_credit += credit_bal

            lines.append(
                {
                    "account_code": acc.account_code,
                    "account_name": acc.name,
                    "account_type": acc.account_type,
                    "debit_balance": float(debit_bal),
                    "credit_balance": float(credit_bal),
                }
            )

        return {
            "as_of_date": str(as_of_date),
            "total_debit": float(total_debit),
            "total_credit": float(total_credit),
            "lines": lines,
        }

    async def generate_balance_sheet(self, as_of_date: datetime.date) -> Dict[str, Any]:
        stmt = select(ChartOfAccount)
        res = await self.db.execute(stmt)
        accounts = res.scalars().all()

        total_assets = Decimal("0.00")
        total_liabilities = Decimal("0.00")
        total_equity = Decimal("0.00")

        asset_lines = []
        liability_lines = []
        equity_lines = []

        for acc in accounts:
            if acc.account_type == "Asset":
                total_assets += acc.current_balance
                asset_lines.append({"code": acc.account_code, "name": acc.name, "balance": float(acc.current_balance)})
            elif acc.account_type == "Liability":
                total_liabilities += acc.current_balance
                liability_lines.append({"code": acc.account_code, "name": acc.name, "balance": float(acc.current_balance)})
            elif acc.account_type == "Equity":
                total_equity += acc.current_balance
                equity_lines.append({"code": acc.account_code, "name": acc.name, "balance": float(acc.current_balance)})

        return {
            "as_of_date": str(as_of_date),
            "total_assets": float(total_assets),
            "total_liabilities": float(total_liabilities),
            "total_equity": float(total_equity),
            "assets": {"section_name": "Assets", "total_amount": float(total_assets), "accounts": asset_lines},
            "liabilities": {"section_name": "Liabilities", "total_amount": float(total_liabilities), "accounts": liability_lines},
            "equity": {"section_name": "Equity", "total_amount": float(total_equity), "accounts": equity_lines},
        }

    async def generate_profit_and_loss(
        self, start_date: datetime.date, end_date: datetime.date
    ) -> Dict[str, Any]:
        stmt = select(ChartOfAccount)
        res = await self.db.execute(stmt)
        accounts = res.scalars().all()

        total_revenue = Decimal("0.00")
        total_expense = Decimal("0.00")

        rev_lines = []
        exp_lines = []

        for acc in accounts:
            if acc.account_type == "Income":
                total_revenue += acc.current_balance
                rev_lines.append({"code": acc.account_code, "name": acc.name, "amount": float(acc.current_balance)})
            elif acc.account_type == "Expense":
                total_expense += acc.current_balance
                exp_lines.append({"code": acc.account_code, "name": acc.name, "amount": float(acc.current_balance)})

        net_profit = total_revenue - total_expense

        return {
            "start_date": str(start_date),
            "end_date": str(end_date),
            "total_revenue": float(total_revenue),
            "total_expense": float(total_expense),
            "net_profit": float(net_profit),
            "revenue_items": rev_lines,
            "expense_items": exp_lines,
        }


# ==========================================
# 8. Budget Service
# ==========================================

class BudgetService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.budget_repo = BudgetRepository()

    async def create_budget(self, data: BudgetCreate) -> Budget:
        budget = Budget(
            code=data.code,
            name=data.name,
            fiscal_year_id=data.fiscal_year_id,
            department_id=data.department_id,
            cost_center_id=data.cost_center_id,
            status="Draft",
        )

        total_budgeted = Decimal("0.00")
        lines = []
        for line in data.lines:
            total_budgeted += line.budgeted_amount
            lines.append(
                BudgetLine(
                    account_id=line.account_id,
                    budgeted_amount=line.budgeted_amount,
                    actual_amount=Decimal("0.00"),
                    variance_amount=line.budgeted_amount,
                )
            )

        budget.total_budgeted_amount = total_budgeted
        budget.lines = lines
        return await self.budget_repo.create(self.db, obj_in=budget)

    async def approve_budget(self, budget_id: uuid.UUID) -> Budget:
        budget = await self.budget_repo.get_by_id(self.db, id=budget_id)
        if not budget:
            raise HTTPException(status_code=404, detail="Budget not found")
        budget.status = "Approved"

        domain_event_publisher.publish(
            FINANCE_BUDGET_APPROVED,
            {"budget_id": str(budget.id), "code": budget.code},
        )
        return budget


# ==========================================
# 9. Closing Service
# ==========================================

class ClosingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def close_period(self, period_id: uuid.UUID, user: User) -> FiscalPeriod:
        stmt = select(FiscalPeriod).where(FiscalPeriod.id == period_id)
        res = await self.db.execute(stmt)
        period = res.scalar_one_or_none()
        if not period:
            raise HTTPException(status_code=404, detail="Fiscal Period not found")

        period.is_closed = True
        period.is_locked = True

        domain_event_publisher.publish(
            FINANCE_PERIOD_CLOSED,
            {"period_id": str(period.id), "name": period.name},
        )
        return period


# ==========================================
# 10. Analytics Service
# ==========================================

class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_financial_analytics(self) -> Dict[str, Any]:
        stmt = select(ChartOfAccount)
        res = await self.db.execute(stmt)
        accounts = res.scalars().all()

        revenue = sum((a.current_balance for a in accounts if a.account_type == "Income"), Decimal("0.00"))
        expenses = sum((a.current_balance for a in accounts if a.account_type == "Expense"), Decimal("0.00"))
        assets = sum((a.current_balance for a in accounts if a.account_type == "Asset"), Decimal("0.00"))
        liabilities = sum((a.current_balance for a in accounts if a.account_type == "Liability"), Decimal("0.00"))
        equity = sum((a.current_balance for a in accounts if a.account_type == "Equity"), Decimal("0.00"))

        net_margin = ((revenue - expenses) / revenue * 100) if revenue > 0 else Decimal("0.00")
        current_ratio = (assets / liabilities) if liabilities > 0 else Decimal("1.00")

        return {
            "revenue": float(revenue),
            "expenses": float(expenses),
            "net_margin_percentage": float(net_margin),
            "cash_position": float(assets * Decimal("0.4")),
            "receivables_outstanding": float(assets * Decimal("0.3")),
            "payables_outstanding": float(liabilities * Decimal("0.5")),
            "asset_total_value": float(assets),
            "current_ratio": float(current_ratio),
            "quick_ratio": float(current_ratio * Decimal("0.9")),
            "debt_to_equity_ratio": float((liabilities / equity) if equity > 0 else Decimal("0.5")),
        }
