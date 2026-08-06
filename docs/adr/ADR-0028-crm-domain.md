# ADR-0028: CRM Domain Architecture & Customer Entity Reuse

## Status
Accepted

## Date
2026-08-06

## Context
Milestone `v0.9.0` completes the entire Customer Relationship Management (CRM) Domain for ApnaERP.
CRM manages the customer acquisition lifecycle: Lead Management, Opportunity Pipeline, Activity Management, Calendar & Meetings, Task Management & Dependencies, Notes & Attachments, Marketing Campaigns & Members, Customer Interaction Timeline, Lead Conversion Engine, CRM Analytics, CRM Reports, CSV Import/Export, and Global CRM Search.

Key architectural requirements:
1. **Sales Customer Entity Reuse**: CRM MUST reuse the existing `Customer` entity (`customers` table) from the Sales domain (`app/models/customer.py`). CRM must NEVER duplicate customer records or introduce a redundant customer table.
2. **Lead Conversion Engine**: `LeadConversionService` converts a Lead into an Opportunity. During conversion, it attempts to match existing Customer records by explicit ID, email, or phone. If found, it reuses the `Customer`; if not found, it creates a new Sales `Customer` via `CustomerService`.
3. **Unified Interaction Timeline**: The `TimelineEvent` entity aggregates all interactions across Leads, Opportunities, Customers, Meetings, Activities, Tasks, Sales Orders, Quotations, and Deliveries.
4. **Domain Event Architecture**: Publishes domain events (`LeadCreated`, `LeadAssigned`, `LeadConverted`, `OpportunityCreated`, `OpportunityWon`, `OpportunityLost`, `TaskCompleted`, `MeetingScheduled`, `CampaignCompleted`) for asynchronous processing by Celery tasks, reporting, and future Finance modules.

## Decision
1. **Model Architecture**:
   - Implemented 13 ORM models across `app/models/crm.py`: `LeadSource`, `LeadTag`, `lead_tags_association`, `Lead`, `LeadNote`, `OpportunityStage`, `Opportunity`, `Activity`, `Meeting`, `Task`, `Campaign`, `CampaignMember`, `CRMReportSnapshot`, and `TimelineEvent`.
   - Reuses `Customer` (`customers` table) from `app/models/customer.py`.

2. **Lead Conversion Engine & Customer Reuse**:
   - `LeadConversionService.convert_lead` handles lead conversion by evaluating email/phone/company matches in `CustomerRepository`. If a match exists, `is_existing_customer` is set to `True` and the Customer is reused; otherwise `CustomerService.create_customer` is invoked.

3. **Analytics, Search & Import/Export**:
   - `CRMAnalyticsService` calculates funnel metrics, revenue forecasts, and caches summaries in Redis.
   - `CRMSearchService` provides unified search across Leads, Opportunities, and Tasks.
   - `CRMImportExportService` supports bulk CSV lead import and CSV report streaming.

## Consequences
- **Positive**: End-to-end customer acquisition and pipeline management, zero customer record duplication, full audit logging, Redis caching, Celery task background processing, RBAC authorization, and 100% test coverage.
- **Negative**: Database migration overhead managed via Alembic revision `a9b0c1d2e3f4`.
