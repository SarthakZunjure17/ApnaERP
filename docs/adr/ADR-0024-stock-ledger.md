# ADR-0024: Inventory Stock Management Engine & Immutability Architecture

## Status
Approved

## Date
2026-07-30

## Context
Enterprise inventory operations require strict tracking, auditability, and historical accuracy for physical stock movements across products, warehouses, and storage locations. Direct mutation of stock levels introduces race conditions, audit gaps, and data corruption risks.

## Decision
1. **Immutable Stock Ledger (`StockLedger`)**: All inventory movements (Opening Stock, Purchase Receipt, Sales Issue, Stock Adjustments, Transfers, Production Consumption, etc.) MUST be recorded as immutable rows in `StockLedger`. Updating or deleting `StockLedger` entries is strictly prohibited.
2. **Running Balance Calculation**: Every ledger record maintains a calculated `running_balance` for the target `(product_id, warehouse_id, location_id)` tuple computed sequentially upon insertion.
3. **Derived Stock Balances (`StockBalance`)**: Current stock quantities are stored in `StockBalance` as a read-optimized projection/cache table. It is derived from `StockLedger` history and can be recalculated or repaired on demand.
4. **Negative Stock Enforcement**: Controlled via `Product.allow_negative_stock`. If disabled (`False`), transactions that would drive running balance below zero are blocked with `ValidationException`.
5. **Adjustment Workflow**: Stock adjustments follow a 3-stage lifecycle (`Draft` -> `Approved` -> `Applied`). Applying an adjustment generates a `STOCK_ADJUSTMENT` ledger entry.

## Consequences
- **Positive**: Complete audit trail of every stock change, race-condition free running balances, high-performance projection reads via `StockBalance`, and full compliance with financial/ERP inventory accounting standards.
- **Negative**: Higher storage requirements for ledger rows, managed via database indexes and eventual archiving.
