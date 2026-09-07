# CRM Foundation (v0.9.0)

## 1. Overview & Purpose
The **CRM Foundation** milestone (`v0.9.0`) introduces the initial Customer Relationship Management subsystem in ApnaERP. It provides comprehensive lead lifecycle tracking, opportunity pipeline management, atomic lead conversion with canonical customer reuse, CRM activity logging, role-based access control, and strict architectural isolation from Inventory, Finance, and Sales order processing.

```
+=============================================================================+
|                                  CRM LEAD                                   |
|   (LEAD-YYYY-XXXXX, Lifecycle: NEW -> CONTACTED -> QUALIFIED -> CONVERTED)  |
|                                       \                                     |
|                                        +--> LOST (Terminal)                 |
+=============================================================================+
                                      |
                       [Atomic Lead Conversion]
            (Concurrency Lock, Deduplication, Reuses Customer)
                                      |
                                      +-------------------------------+
                                      |                               |
                                      v                               v
+=============================================================================+
|                         CANONICAL CUSTOMER MASTER                           |
|             (Existing Customer Reused or CUST-YYYY-XXXXX Created)           |
+=============================================================================+
                                      |
                                      v (Optional Opportunity Linking)
+=============================================================================+
|                              CRM OPPORTUNITY                                |
|  (OPP-YYYY-XXXXX, Pipeline: PROSPECTING -> QUALIFICATION -> PROPOSAL ->     |
|                             NEGOTIATION -> WON / LOST)                      |
+=============================================================================+
                                      ^
                                      | (Entity Reference)
+=============================================================================+
|                               CRM ACTIVITIES                                |
|     (Calls, Meetings, Emails, Notes, Follow-ups with Status Lifecycle)      |
+=============================================================================+
```

---

## 2. Lead Management Subsystem

### 2.1 Lead Entity Structure
- **Entity Model**: `Lead` (`leads` table)
- **Key Fields**:
  - `id`: UUID primary key
  - `lead_code`: Sequential human-readable identifier (`LEAD-YYYY-XXXXX`)
  - `first_name`, `last_name`, `company`, `title`
  - `email`, `phone`, `website`, `source_id`
  - `status`: State machine status (`NEW`, `CONTACTED`, `QUALIFIED`, `CONVERTED`, `LOST`)
  - `score`: Dynamic quality/readiness score (0–100)
  - `estimated_value`: `Numeric(18, 2)` prospective deal value
  - `assigned_to_id`: Assigned Sales Representative / User ID
  - `is_converted`, `converted_at`, `converted_customer_id`, `converted_opportunity_id`
  - `is_deleted`, `deleted_at` (soft delete pattern)

### 2.2 Lead Lifecycle State Machine
Leads progress strictly along predefined lifecycle transitions:
- `NEW` $\rightarrow$ `CONTACTED` or `LOST`
- `CONTACTED` $\rightarrow$ `QUALIFIED` or `LOST`
- `QUALIFIED` $\rightarrow$ `CONVERTED` or `LOST`
- `CONVERTED`: Terminal state (immutable; duplicate conversion or field edits rejected)
- `LOST`: Terminal state (immutable; invalid transitions rejected)

### 2.3 Lead Operations & Endpoints
- `POST /api/v1/crm/leads`: Create lead with duplicate check and automated sequential numbering.
- `GET /api/v1/crm/leads`: Paginated list with filtering by `status`, `assigned_to_id`, `source_id`, and full-text search.
- `GET /api/v1/crm/leads/{id}`: Fetch lead by ID with loaded notes, tags, source, and assigned user.
- `PUT /api/v1/crm/leads/{id}`: Update lead with transition validation and score recalculation.
- `POST /api/v1/crm/leads/{id}/assign`: Assign lead ownership to a sales team member.
- `POST /api/v1/crm/leads/{id}/notes`: Add internal or pinned collaboration notes.
- `DELETE /api/v1/crm/leads/{id}`: Soft delete lead.

---

## 3. Opportunity Management Subsystem

### 3.1 Opportunity Entity Structure
- **Entity Model**: `Opportunity` (`opportunities` table)
- **Key Fields**:
  - `id`: UUID primary key
  - `opportunity_code`: Sequential identifier (`OPP-YYYY-XXXXX`)
  - `title`: Commercial deal summary
  - `customer_id`: Canonical customer reference (nullable for unassigned leads)
  - `lead_id`: Originating lead reference (nullable for direct opportunities)
  - `stage_id`: Pipeline stage reference
  - `expected_revenue`: `Numeric(18, 2)` anticipated revenue
  - `probability`: `Numeric(5, 2)` closing probability percentage (0%–100%)
  - `expected_closing_date`: Target close date
  - `status`: Deal status (`Open`, `Won`, `Lost`)
  - `owner_id`: Sales representative owner
  - `win_loss_reason`: Commercial outcome rationale

### 3.2 Pipeline Stages & Progression
Standard stage pipeline with default win probabilities:
1. `PROSPECTING` (10% default probability)
2. `QUALIFICATION` (30% default probability)
3. `PROPOSAL` (60% default probability)
4. `NEGOTIATION` (80% default probability)
5. `WON` (100% probability, status: `Won`, Terminal)
6. `LOST` (0% probability, status: `Lost`, Terminal)

- Forward transitions and backward revisions in `Open` status are supported.
- Closed deals (`Won` / `Lost`) are terminal; stage changes or general edits on closed opportunities are rejected.

### 3.3 Opportunity Endpoints
- `POST /api/v1/crm/opportunities`: Create opportunity.
- `GET /api/v1/crm/opportunities`: List opportunities with filtering and search.
- `GET /api/v1/crm/opportunities/{id}`: Retrieve detailed opportunity with stage, customer, and owner.
- `PUT /api/v1/crm/opportunities/{id}`: Update deal details.
- `POST /api/v1/crm/opportunities/{id}/stage`: Advance pipeline stage.
- `POST /api/v1/crm/opportunities/{id}/win-loss`: Record closing outcome (`Won` / `Lost`) with reason and notes.
- `DELETE /api/v1/crm/opportunities/{id}`: Soft delete opportunity.

---

## 4. Controlled Lead Conversion Subsystem

The lead conversion operation provides an atomic, transactional transition from qualification to account & opportunity generation:

### 4.1 Conversion Guardrails
1. **Pessimistic Concurrency Lock**: Executes `SELECT ... FOR UPDATE` on the lead record to eliminate race conditions.
2. **Duplicate Conversion Protection**: Re-conversion attempts on already converted leads are immediately rejected.
3. **Qualification Rule**: Only leads in `QUALIFIED` status are permitted to convert.
4. **Canonical Customer Master Reuse**:
   - If `existing_customer_id` is specified, verifies and links the existing canonical customer.
   - Searches for an existing Customer by matching `lead.email` or `lead.phone`.
   - If matched, links to the existing Customer master without creating redundant records.
   - If no match is found, creates a single canonical `Customer` (`CUST-YYYY-XXXXX`) in the Sales domain with a primary `CustomerContact`.
5. **Optional Opportunity Creation**: Creates an Opportunity in `QUALIFICATION` stage linked to the resolved customer and lead when requested.
6. **Lead Mutation**: Marks lead `is_converted=True`, `status="CONVERTED"`, `converted_at=now()`, and records target customer and opportunity IDs.

### 4.2 Endpoint
- `POST /api/v1/crm/leads/{id}/convert`: Execute atomic lead conversion.

---

## 5. CRM Activities & Interactions

### 5.1 Activity Model & Types
- **Entity Model**: `Activity` (`activities` table)
- **Supported Types**:
  - `Call`, `Meeting`, `Email`, `Note`, `Follow_up`
- **Fields**: `subject`, `description`, `status` (`Pending`, `In_Progress`, `Completed`, `Cancelled`), `priority`, `due_date`, `completed_at`, `owner_id`, `lead_id`, `opportunity_id`, `customer_id`.

### 5.2 Endpoints
- `POST /api/v1/crm/activities`: Create activity linked to lead, opportunity, or customer.
- `GET /api/v1/crm/activities`: Filter activities by entity link, type, status, and search query.
- `GET /api/v1/crm/activities/{id}`: Retrieve activity.
- `PUT /api/v1/crm/activities/{id}`: Update activity details.
- `POST /api/v1/crm/activities/{id}/complete`: Mark activity as `Completed` with `completed_at` timestamp.
- `DELETE /api/v1/crm/activities/{id}`: Delete activity.

---

## 6. RBAC & Security Matrix

### 6.1 CRM Permissions
| Permission | Description |
| :--- | :--- |
| `crm.lead.create` | Create new CRM leads |
| `crm.lead.read` | View CRM leads and notes |
| `crm.lead.update` | Update CRM lead details and statuses |
| `crm.lead.delete` | Soft delete CRM leads |
| `crm.lead.convert` | Convert qualified leads into customers/opportunities |
| `crm.opportunity.create` | Create CRM opportunities |
| `crm.opportunity.read` | View CRM opportunities and stages |
| `crm.opportunity.update` | Update opportunity details |
| `crm.opportunity.delete` | Soft delete CRM opportunities |
| `crm.opportunity.stage` | Change opportunity pipeline stage and win/loss |
| `crm.activity.create` | Log new CRM activities |
| `crm.activity.read` | View CRM activities |
| `crm.activity.update` | Update and complete CRM activities |
| `crm.activity.delete` | Remove CRM activities |

### 6.2 Role Mapping
- **CRM Manager**: Full access to all `crm.*` actions and lead conversion.
- **Sales Representative**: Create, view, update, convert leads, manage opportunities, and record activities.
- **CRM Viewer / Sales Viewer**: Read-only access (`crm.lead.read`, `crm.opportunity.read`, `crm.activity.read`).

---

## 7. Audit Logging & Domain Events

### 7.1 Canonical AuditLog Events
Every state mutation creates an immutable `AuditLog` entry:
- `CREATE_LEAD`, `UPDATE_LEAD`, `ASSIGN_LEAD`, `CONVERT_LEAD`, `DELETE_LEAD`
- `CREATE_OPPORTUNITY`, `UPDATE_OPPORTUNITY`, `CHANGE_STAGE_OPPORTUNITY`, `WIN_LOSS_OPPORTUNITY`, `DELETE_OPPORTUNITY`
- `CREATE_ACTIVITY`, `UPDATE_ACTIVITY`, `COMPLETE_ACTIVITY`, `DELETE_ACTIVITY`

### 7.2 Domain Events
Published on the internal event bus for observability and cross-domain events:
- `CRM_LEAD_CREATED` (`crm.lead.created`)
- `CRM_LEAD_ASSIGNED` (`crm.lead.assigned`)
- `CRM_LEAD_CONVERTED` (`crm.lead.converted`)
- `CRM_OPPORTUNITY_CREATED` (`crm.opportunity.created`)
- `CRM_OPPORTUNITY_STAGE_CHANGED` (`crm.opportunity.stage_changed`)

---

## 8. Architectural Boundaries & Domain Isolation

1. **Reuses Sales Customer Master**: CRM directly associates with `Customer` (`customers` table) from the Sales domain. No duplicate contact or customer master is introduced.
2. **Zero Inventory Mutations**: CRM operations do NOT touch `StockBalance`, `StockLedger`, or warehouse tables.
3. **Zero Finance Modifications**: CRM operations do NOT create General Ledger entries, journal vouchers, invoices, accounts receivable, or accounts payable.
4. **Zero Sales Order Creation**: CRM does not automatically create `SalesOrder` records. Sales Orders are created solely within the Sales domain.
5. **No AI or Marketing Automation Overreach**: v0.9.0 establishes the pure CRM Foundation without speculative background campaigns or external mail integrations.
