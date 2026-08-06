# ADR-0030: Finance Operations & Financial Reporting Architecture

- **Status**: Approved
- **Date**: 2026-08-06
- **Authors**: Principal Software Architect & Financial Systems Architect
- **Domain**: Finance Operations, Financial Reporting & Asset Management

## Context & Problem Statement
ApnaERP Release `v1.0.0` established the **Finance Core** engine (Chart of Accounts, Fiscal Calendar, Currencies, Cost Centers, Tax Categories, Posting Rules, and Double-Entry Journal Engine).

To complete the entire Finance Domain for Release `v1.1.0`, ApnaERP required operational accounting capabilities:
1. Accounts Receivable (Invoices, Credit/Debit Notes, Customer Ledgers, Aging, Statements).
2. Accounts Payable (Bills, Credit/Debit Notes, Supplier Ledgers, Aging, Vendor Statements).
3. Payments & Allocations (Payment & Receipt Vouchers, Partial Allocations, Cash/Bank Disbursements).
4. Bank Management & Reconciliation (Bank Accounts, Transactions, Statement Imports, Auto/Manual Matching).
5. Fixed Assets & Depreciation (Asset Register, Acquisitions, Disposals, StraightLine/WDV Depreciation Schedules).
6. Budget Management (Annual/Department Budgets, Line Items, Approvals, Revisions, Variance Analysis).
7. Financial Statements (Trial Balance, Balance Sheet, Profit & Loss, Cash Flow Statement, Ledgers).
8. Financial Closing (Period Closing, Year-End Closing, Period Lock/Reopen).
9. Finance Analytics & Reporting (Day Book, Cash Book, Financial Ratios, Executive Dashboard with Redis caching).

A key strict architectural constraint was that **no operational module may bypass Journal Posting** or edit General Ledger balances directly.

## Decision Drivers
- **Central Journal Engine Enforcement**: All financial operations post strictly through `Journal` & `JournalLine` entries.
- **Sub-Ledger Reconciliation**: `CustomerLedgerEntry` and `SupplierLedgerEntry` track running balances tied 1-to-1 to posted journals.
- **Bank Reconciliation Integrity**: Bank statement matching matches lines against `BankTransaction` entries without mutating posted journals.
- **Immutability & Auditability**: Posted vouchers cannot be deleted; counter-balancing reversal journals (`REV-`) ensure full audit trail integrity.
- **Backward Compatibility**: Reuses existing `Customer`, `Supplier`, `Department`, and Finance Core models without schema regression.

## Design Decisions

1. **Operational ORM Schema (`app/models/finance_ops.py`)**:
   - Created 25 tables supporting AR, AP, Payments, Bank Accounts, Statement Reconciliation, Fixed Assets, Depreciation Schedules, Budgets, and Statement Snapshots.
2. **Posting Engine Integration (`app/services/finance_ops_services.py`)**:
   - Added `post_double_entry_journal` helper to `PostingEngineService` to handle transactional posting and GL balance updating in a single atomic transaction.
3. **Event-Driven Architecture (`app/core/domain_events.py`)**:
   - Published domain events: `PaymentReceived`, `PaymentMade`, `BankReconciled`, `AssetCreated`, `AssetDisposed`, `DepreciationPosted`, `PeriodClosed`, `YearClosed`, `BudgetApproved`, `FinancialStatementGenerated`.
4. **Celery Background Tasks (`app/tasks/finance_ops_tasks.py`)**:
   - Background processing for batch monthly depreciation, recurring vouchers, budget threshold alerts, statement snapshotting, closing checks, and Redis analytics cache updates.
5. **RBAC Permissions (`app/db/seed_rbac.py`)**:
   - Seeded permissions (`finance.receivable.*`, `finance.payable.*`, `finance.payment.*`, `finance.bank.*`, `finance.reconciliation.*`, `finance.asset.*`, `finance.depreciation.*`, `finance.statement.*`, `finance.budget.*`, `finance.analytics.*`) assigned to `Finance Manager`, `Chief Accountant`, and `Super Admin`.

## Consequences & Verification
- **Positive**: Complete Finance domain capability covering all operational accounting requirements.
- **Verification**: Executed [`tests/test_finance_ops.py`](file:///D:/sarthak/projects/ApnaERP/tests/test_finance_ops.py) with 100% pass rate across 6 test suites.
