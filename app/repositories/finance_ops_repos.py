from typing import Any, List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.repositories.base_repository import BaseRepository


class CustomerInvoiceRepository(BaseRepository[CustomerInvoice, Any, Any]):
    def __init__(self):
        super().__init__(CustomerInvoice)

    async def get_by_number(self, db: AsyncSession, invoice_number: str) -> Optional[CustomerInvoice]:
        stmt = select(CustomerInvoice).where(CustomerInvoice.invoice_number == invoice_number)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_customer(self, db: AsyncSession, customer_id: uuid.UUID) -> List[CustomerInvoice]:
        stmt = select(CustomerInvoice).where(CustomerInvoice.customer_id == customer_id)
        res = await db.execute(stmt)
        return list(res.scalars().all())


class SupplierBillRepository(BaseRepository[SupplierBill, Any, Any]):
    def __init__(self):
        super().__init__(SupplierBill)

    async def get_by_number(self, db: AsyncSession, bill_number: str) -> Optional[SupplierBill]:
        stmt = select(SupplierBill).where(SupplierBill.bill_number == bill_number)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_supplier(self, db: AsyncSession, supplier_id: uuid.UUID) -> List[SupplierBill]:
        stmt = select(SupplierBill).where(SupplierBill.supplier_id == supplier_id)
        res = await db.execute(stmt)
        return list(res.scalars().all())


class CustomerLedgerRepository(BaseRepository[CustomerLedgerEntry, Any, Any]):
    def __init__(self):
        super().__init__(CustomerLedgerEntry)

    async def get_by_customer(self, db: AsyncSession, customer_id: uuid.UUID) -> List[CustomerLedgerEntry]:
        stmt = (
            select(CustomerLedgerEntry)
            .where(CustomerLedgerEntry.customer_id == customer_id)
            .order_by(CustomerLedgerEntry.posting_date.asc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())


class SupplierLedgerRepository(BaseRepository[SupplierLedgerEntry, Any, Any]):
    def __init__(self):
        super().__init__(SupplierLedgerEntry)

    async def get_by_supplier(self, db: AsyncSession, supplier_id: uuid.UUID) -> List[SupplierLedgerEntry]:
        stmt = (
            select(SupplierLedgerEntry)
            .where(SupplierLedgerEntry.supplier_id == supplier_id)
            .order_by(SupplierLedgerEntry.posting_date.asc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())


class ReceiptVoucherRepository(BaseRepository[ReceiptVoucher, Any, Any]):
    def __init__(self):
        super().__init__(ReceiptVoucher)


class PaymentVoucherRepository(BaseRepository[PaymentVoucher, Any, Any]):
    def __init__(self):
        super().__init__(PaymentVoucher)


class PaymentAllocationRepository(BaseRepository[PaymentAllocation, Any, Any]):
    def __init__(self):
        super().__init__(PaymentAllocation)


class BankAccountRepository(BaseRepository[BankAccount, Any, Any]):
    def __init__(self):
        super().__init__(BankAccount)


class BankTransactionRepository(BaseRepository[BankTransaction, Any, Any]):
    def __init__(self):
        super().__init__(BankTransaction)


class BankStatementRepository(BaseRepository[BankStatement, Any, Any]):
    def __init__(self):
        super().__init__(BankStatement)


class BankReconciliationRepository(BaseRepository[BankReconciliation, Any, Any]):
    def __init__(self):
        super().__init__(BankReconciliation)


class AssetCategoryRepository(BaseRepository[AssetCategory, Any, Any]):
    def __init__(self):
        super().__init__(AssetCategory)


class FixedAssetRepository(BaseRepository[FixedAsset, Any, Any]):
    def __init__(self):
        super().__init__(FixedAsset)


class DepreciationScheduleRepository(BaseRepository[DepreciationSchedule, Any, Any]):
    def __init__(self):
        super().__init__(DepreciationSchedule)


class BudgetRepository(BaseRepository[Budget, Any, Any]):
    def __init__(self):
        super().__init__(Budget)


class FinancialStatementSnapshotRepository(BaseRepository[FinancialStatementSnapshot, Any, Any]):
    def __init__(self):
        super().__init__(FinancialStatementSnapshot)
