# ADR-0029: Finance Core Implementation

## Status
Accepted

## Context
ApnaERP requires a central financial accounting engine to serve as the single source of financial truth across all enterprise domains (Payroll, Procurement, Sales, Inventory, and future modules). To preserve module autonomy and audit integrity, external domains cannot directly mutate General Ledger balances; instead, all financial activity flows through double-entry balanced Journal Entries and automated Posting Rules.

## Decision
1. **Double-Entry Mandate**: Implemented mandatory double-entry accounting where `Total Debit == Total Credit` for every Journal Entry.
2. **Entity Models**: Defined 15 core financial entities:
   - AccountGroup, ChartOfAccount
   - FiscalYear, FiscalPeriod
   - Currency, ExchangeRate
   - CostCenter, AccountingDimension
   - JournalType, Journal, JournalLine
   - TaxCategory, TaxRate
   - PostingRule, AccountingEvent
3. **Immutability & Reversals**: Posted journals cannot be modified or deleted. Reversals create new counter-balancing `REV-` journals with linked audit IDs (`reversed_journal_id`).
4. **Integration via Queue**: Created `FinancialPostingQueue` and background Celery tasks (`process_financial_posting_queue_task`) to transform domain events into General Ledger postings.
5. **Security & RBAC**: Established granular permissions (`finance.accounts.*`, `finance.journal.*`, `finance.posting.*`, `finance.tax.*`, `finance.currency.*`, `finance.costcenter.*`, `finance.fiscal.*`) and seeded `Finance Manager` and `Chief Accountant` roles.

## Consequences
- Guarantees strict financial ledger consistency and non-repudiation across ApnaERP.
- Preserves backward compatibility with all pre-existing domains.
- Facilitates future financial reporting, AR/AP, and bank reconciliation extensions without schema restructuring.
