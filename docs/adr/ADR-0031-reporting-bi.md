# ADR-0031: Enterprise Reporting & Business Intelligence Architecture

- **Status**: Approved
- **Date**: 2026-08-07
- **Authors**: Principal Software Architect & Business Intelligence Architect
- **Domain**: Reporting & Business Intelligence

## Context & Problem Statement
ApnaERP Release `v1.1.0` established complete operational accounting in Finance Operations.

For Release `v1.2.0`, ApnaERP required a comprehensive **Enterprise Reporting & Business Intelligence** platform capable of aggregating data across all 8 operational domains (Platform, HR, Payroll, Inventory, Procurement, Sales, CRM, Finance) without duplicating business logic or mutating operational data.

## Decision Drivers
- **Non-Mutating Read-Only Aggregation**: Reporting & BI must read existing domain entities and perform on-the-fly aggregations without altering underlying business states.
- **Dynamic Report Builder**: Support dynamic queries over domain datasources with customizable column selection, filtering, sorting, grouping, and calculated fields.
- **Scheduled Delivery**: Automated background report execution on configurable cron/frequency schedules, generating exports and delivering via `NotificationService` and `email_service`.
- **Multi-Format Export Engine**: Support PDF, Excel, CSV, and JSON exports integrated with the core `File` repository.
- **High-Performance Caching**: Redis cache integration for high-impact executive dashboards and KPI metrics.

## Design Decisions

1. **Reporting ORM Schema (`app/models/reporting.py`)**:
   - Created 10 entities: `Dashboard`, `DashboardWidget`, `KPI`, `KPIMetric`, `ReportTemplate`, `SavedReport`, `ScheduledReport`, `ReportExecution`, `AnalyticsSnapshot`, `ChartConfiguration`.
2. **Domain Services Layer (`app/services/reporting_services.py`)**:
   - `DashboardService`: System dashboards (Global, HR, Payroll, Inventory, Procurement, Sales, CRM, Finance) + Custom Dashboards, Widget Management, Redis caching.
   - `KPIService`: Dynamic calculation for all KPIs across 8 modules, recording metrics over time, threshold alert detection, Redis caching.
   - `AnalyticsService`: Period comparisons, growth rate calculations (% YoY/MoM), trend aggregations across modules, forecast-ready metrics.
   - `ReportBuilderService`: Dynamic query builder reading existing domain models (Employee, PayrollRun, StockBalance, PurchaseOrder, SalesOrder, Lead, Opportunity, CustomerInvoice, SupplierBill, JournalLine, etc.), custom columns, filtering, sorting, grouping, calculated fields, saved reports.
   - `ScheduledReportService`: Schedule processing, cron evaluation, trigger execution, email notification dispatch via `NotificationService` and `email_service`.
   - `ExportService`: Generates PDF, Excel, CSV, JSON exports, saving output to `File` repository.
   - `ChartService`: Formats data payloads into chart configs (Line, Bar, Area, Pie, Donut, Stacked Bar, Heatmap, Trend).
   - `GlobalSearchService`: Global search over reports, dashboards, KPIs, saved reports.
3. **Event-Driven Integration (`app/core/domain_events.py`)**:
   - Published domain events: `ReportGenerated`, `DashboardViewed`, `ScheduledReportCompleted`, `KPIUpdated`, `AnalyticsCalculated`.
4. **Celery Background Tasks (`app/tasks/reporting_tasks.py`)**:
   - Background processing for due scheduled reports, pre-calculating periodic analytics snapshots, refreshing active KPIs, and warming up dashboard cache.
5. **RBAC Permissions (`app/db/seed_rbac.py`)**:
   - Seeded permissions (`report.dashboard.*`, `report.analytics.*`, `report.builder.*`, `report.kpi.*`, `report.export.*`, `report.schedule.*`).

## Consequences & Verification
- **Positive**: Complete Reporting & BI capability covering all 8 operational domains.
- **Verification**: Executed [`tests/test_reporting_bi.py`](file:///D:/sarthak/projects/ApnaERP/tests/test_reporting_bi.py) with 100% pass rate across 6 test suites.
