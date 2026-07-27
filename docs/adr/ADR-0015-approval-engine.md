# ADR-0015: Enterprise Approval Workflow Engine (Platform)

## Status
Accepted

## Context
In an Enterprise ERP platform (ApnaERP), multiple business domain modules—such as Leave Management, Expense Claims, Purchase Orders, Asset Management, Payroll, and Inventory—require flexible, multi-step, role-based approval workflows. Hardcoding approval logic into individual domain modules leads to code duplication, inconsistent audit trails, brittle state machines, and maintenance overhead.

We need a generic, domain-agnostic, reusable Enterprise Approval Workflow Engine at the Platform layer that can be integrated with any business entity (`entity_type`, `entity_id`).

## Decision
We implemented a platform-level approval engine comprising four core entities:
1. `ApprovalWorkflow`: Workflow definitions specifying unique `code`, `name`, `module_name`, and active status.
2. `ApprovalStep`: Sequenced step definitions (`workflow_id`, `step_number`, `approver_role_id`, `required_approvals`, `auto_approve`).
3. `ApprovalRequest`: Runtime approval execution instance referencing generic target entities (`entity_type`, `entity_id`) and managing approval status (`Draft`, `Pending`, `Approved`, `Rejected`, `Cancelled`).
4. `ApprovalHistory`: Immutable audit history recording every approval action (`Submitting`, `Approved Step`, `Rejected`, `Cancelled`, `Completed Workflow`), performer, step number, timestamp, and comments.

### State Machine Transition Rules
- `Draft` / Start -> `Pending` (Step 1)
- `Pending` (Step N) -> `Pending` (Step N+1) if more steps remain
- `Pending` (Step N) -> `Approved` if no further steps remain (Terminal State)
- `Pending` (Step N) -> `Rejected` upon rejection (Terminal State)
- `Pending` (Step N) -> `Cancelled` upon cancellation by submitter/admin (Terminal State)

### Key Architectural Rules
- Role-based authorization: Step approvals require the assigned `Role` (`approver_role_id`) or superuser privileges.
- Sequential execution: Step numbers must advance sequentially without skipping steps.
- Decoupled design: Domain modules invoke `ApprovalEngineService.start_workflow(...)` without the approval engine having any dependency on target domain tables.
- Async performance: Invalidation of Redis caches and background Celery notification dispatch on every state transition.

## Consequences
- Single, consistent approval engine across all present and future ApnaERP modules.
- Strict immutable auditability of all approval actions and decision history.
- Zero coupling between platform approval engine and specific business domain models.
