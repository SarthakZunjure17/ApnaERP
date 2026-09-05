# Warehouse Operations (v0.6.2)

## 1. Overview & Architecture

Warehouse Operations in ApnaERP v0.6.2 encapsulate the authoritative business workflows for inventory movements across warehouses and storage locations:
1. **Goods Receipt**: Inbound physical stock receipt into a specific warehouse and storage location.
2. **Goods Issue**: Outbound physical stock issue / consumption from a warehouse and storage location.
3. **Stock Transfer**: Inter-warehouse and intra-warehouse movement moving physical stock out of a source location and into a destination location atomically.

### Architectural Flow & Boundary Separation

```
+-------------------------------------------------------------------+
|                        Business Layer                             |
|  GoodsReceipt / GoodsIssue / StockTransfer Documents (DRAFT)      |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|               Posting & Validation Layer                          |
|  - Warehouse, location, and product validation                    |
|  - Inactive/Archived/Non-stockable entity rejection               |
|  - Deterministic balance key sorting (Transfer Deadlock Safety)   |
+-------------------------------------------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|               Stock Engine (v0.6.1 Authorized Engine)             |
|                  StockMovementService                             |
|  - stock_in() / stock_out()                                       |
|  - Negative stock policy validation                               |
|  - Pessimistic row locking on StockBalance                        |
+-------------------------------------------------------------------+
                                  |
                                  v
+---------------------------------+---------------------------------+
|                                 |                                 |
v                                 v                                 v
+-----------------------+ +-----------------------+ +-----------------------+
|     StockBalance      | |      StockLedger      | |       AuditLog        |
| Authoritative Qty     | |  Immutable History    | |  User, Event & Delta  |
+-----------------------+ +-----------------------+ +-----------------------+
```

---

## 2. Core Invariants

1. **StockLedger is Append-Only**: Ledger entries are immutable financial/physical audit records. Posted movements are never modified or deleted.
2. **StockBalance is the Authoritative Quantity Engine**: Current physical stock levels are tracked exclusively in `StockBalance`.
3. **Strict Delegation to StockMovementService**: Business operation services (`GoodsReceiptService`, `GoodsIssueService`, `StockTransferService`) NEVER directly mutate `StockBalance.available_quantity`. All mutations MUST pass through `StockMovementService.stock_in()` and `StockMovementService.stock_out()`.
4. **Document Immutability upon Posting**: Once a document transitions to `Posted`, its attributes and line items are locked. No edits or deletions are permitted.
5. **Multi-Line Transactional Atomicity**: Posting a document processes all line items within a single database transaction. If line $N$ fails (e.g., insufficient stock), all preceding line mutations roll back completely, and the document remains in `Draft`.
6. **Stock Transfer Atomicity & Deadlock Prevention**: Both Source OUT and Destination IN execute within a single transaction. Balances are pre-locked in deterministic lexicographical order `(product_id, warehouse_id, storage_location_id)` to eliminate circular wait deadlocks.
7. **Posting Idempotency**: Documents already in `Posted` or terminal status reject duplicate post attempts with `ValidationException`.

---

## 3. Document Lifecycles

### Goods Receipt
- `Draft` $\rightarrow$ `Posted` (or `Received`)
- `Draft` $\rightarrow$ `Cancelled`
- Draft documents can be edited and deleted. Posted documents are immutable.

### Goods Issue
- `Draft` $\rightarrow$ `Posted` (or `Issued`)
- `Draft` $\rightarrow$ `Cancelled`
- Draft documents can be edited and deleted. Posted documents are immutable.

### Stock Transfer
- `Draft` $\rightarrow$ `Posted` (Single-step atomic transfer)
- Optional Two-Phase Workflow: `Draft` $\rightarrow$ `In Transit` (Dispatch) $\rightarrow$ `Completed` (Receive)
- `Draft` $\rightarrow$ `Cancelled`

---

## 4. Concurrency & Deadlock Prevention in Transfers

When multiple concurrent transfers occur between the same warehouses (e.g., Transfer A: WH1 $\rightarrow$ WH2 and Transfer B: WH2 $\rightarrow$ WH1), naive locking of source before destination leads to database deadlocks.

ApnaERP v0.6.2 solves this with deterministic lock ordering:
1. All unique balance coordinate keys `(product_id, warehouse_id, storage_location_id)` involved in the transfer are gathered.
2. Keys are sorted deterministically using lexicographical tuple comparison:
   ```python
   lock_keys = sorted(balance_keys, key=lambda k: (str(k[0]), str(k[1]), str(k[2] or "")))
   ```
3. `StockBalance` rows are acquired in this exact sequence using `SELECT FOR UPDATE` before applying `stock_out` and `stock_in`.
4. This guarantees a global lock hierarchy, mathematically preventing circular wait condition deadlocks.

---

## 5. API Endpoints

### Canonical Warehouse Routes (`/api/v1/warehouse/*`)
- **Goods Receipts**:
  - `POST /api/v1/warehouse/receipts` — Create Draft Receipt
  - `GET /api/v1/warehouse/receipts` — List Paginated Receipts
  - `GET /api/v1/warehouse/receipts/{id}` — Get Receipt Details
  - `PATCH /api/v1/warehouse/receipts/{id}` — Update Draft Receipt
  - `DELETE /api/v1/warehouse/receipts/{id}` — Delete Draft Receipt
  - `POST /api/v1/warehouse/receipts/{id}/post` — Post Receipt (Atomically triggers `STOCK_IN`)
  - `POST /api/v1/warehouse/receipts/{id}/cancel` — Cancel Draft Receipt
- **Goods Issues**:
  - `POST /api/v1/warehouse/issues` — Create Draft Issue
  - `GET /api/v1/warehouse/issues` — List Paginated Issues
  - `GET /api/v1/warehouse/issues/{id}` — Get Issue Details
  - `PATCH /api/v1/warehouse/issues/{id}` — Update Draft Issue
  - `DELETE /api/v1/warehouse/issues/{id}` — Delete Draft Issue
  - `POST /api/v1/warehouse/issues/{id}/post` — Post Issue (Atomically triggers `STOCK_OUT`)
  - `POST /api/v1/warehouse/issues/{id}/cancel` — Cancel Draft Issue
- **Stock Transfers**:
  - `POST /api/v1/warehouse/transfers` — Create Draft Transfer
  - `GET /api/v1/warehouse/transfers` — List Paginated Transfers
  - `GET /api/v1/warehouse/transfers/{id}` — Get Transfer Details
  - `PATCH /api/v1/warehouse/transfers/{id}` — Update Draft Transfer
  - `DELETE /api/v1/warehouse/transfers/{id}` — Delete Draft Transfer
  - `POST /api/v1/warehouse/transfers/{id}/post` — Post Transfer (Atomically triggers Source OUT + Dest IN)
  - `POST /api/v1/warehouse/transfers/{id}/cancel` — Cancel Draft Transfer

---

## 6. RBAC Permissions

| Permission | Description |
|---|---|
| `inventory.receipt.read` | View goods receipts and receipt lines |
| `inventory.receipt.create` | Create new draft goods receipts |
| `inventory.receipt.update` | Modify draft goods receipts |
| `inventory.receipt.delete` | Delete draft goods receipts |
| `inventory.receipt.post` | Post goods receipts to stock ledger |
| `inventory.issue.read` | View goods issues and issue lines |
| `inventory.issue.create` | Create new draft goods issues |
| `inventory.issue.update` | Modify draft goods issues |
| `inventory.issue.delete` | Delete draft goods issues |
| `inventory.issue.post` | Post goods issues to stock ledger |
| `inventory.transfer.read` | View stock transfers and transfer lines |
| `inventory.transfer.create` | Create new draft stock transfers |
| `inventory.transfer.update` | Modify draft stock transfers |
| `inventory.transfer.delete` | Delete draft stock transfers |
| `inventory.transfer.post` | Post stock transfers to stock ledger |

---

## 7. Future Compatibility & Frozen Boundaries

- **v0.6.3 (Advanced Inventory)**: Batch/lot tracking, serial numbers, expiry dates, reservations, and ATP allocations will hook into the generic `reference_type`/`reference_id`/`metadata_json` fields without altering v0.6.2 warehouse operation contracts.
- **Procurement & Sales**: Automatic PO $\rightarrow$ Receipt and SO $\rightarrow$ Issue conversions remain strictly decoupled in v0.6.2. Business documents accept generic reference fields for seamless forward integration.
