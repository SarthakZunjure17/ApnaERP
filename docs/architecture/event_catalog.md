# ApnaERP Finalized Domain Event Catalog (v1.3.0)

This catalog documents all published domain events across the complete 10-domain ApnaERP platform.

## 1. Platform Domain Events
- `platform.user.created` (`UserCreated`)
- `platform.user.updated` (`UserUpdated`)
- `platform.role.assigned` (`RoleAssigned`)
- `platform.audit.logged` (`AuditLogged`)

## 2. HR Domain Events
- `hr.employee.created` (`EmployeeCreated`)
- `hr.employee.updated` (`EmployeeUpdated`)
- `hr.employee.terminated` (`EmployeeTerminated`)
- `hr.leave.requested` (`LeaveRequested`)
- `hr.leave.approved` (`LeaveApproved`)
- `hr.leave.rejected` (`LeaveRejected`)
- `hr.attendance.checked_in` (`AttendanceCheckedIn`)

## 3. Payroll Domain Events
- `payroll.run.initialized` (`PayrollRunInitialized`)
- `payroll.run.calculated` (`PayrollRunCalculated`)
- `payroll.run.approved` (`PayrollRunApproved`)
- `payroll.run.finalized` (`PayrollRunFinalized`)
- `payroll.payslip.published` (`PayslipPublished`)

## 4. Inventory Domain Events
- `inventory.product.created` (`ProductCreated`)
- `inventory.stock.adjusted` (`StockAdjusted`)
- `inventory.receipt.received` (`GoodsReceiptReceived`)
- `inventory.issue.issued` (`GoodsIssueIssued`)
- `inventory.transfer.completed` (`StockTransferCompleted`)
- `inventory.batch.expired` (`BatchExpired`)

## 5. Procurement Domain Events
- `procurement.requisition.approved` (`PurchaseRequisitionApproved`)
- `procurement.rfq.published` (`RFQPublished`)
- `procurement.quotation.received` (`SupplierQuotationReceived`)
- `procurement.order.approved` (`PurchaseOrderApproved`)
- `procurement.return.processed` (`PurchaseReturnProcessed`)

## 6. Sales Domain Events
- `sales.customer.created` (`CustomerCreated`)
- `sales.quotation.accepted` (`SalesQuotationAccepted`)
- `sales.order.confirmed` (`SalesOrderConfirmed`)
- `sales.delivery.dispatched` (`DeliveryOrderDispatched`)
- `sales.return.processed` (`SalesReturnProcessed`)

## 7. CRM Domain Events
- `crm.lead.created` (`LeadCreated`)
- `crm.lead.converted` (`LeadConverted`)
- `crm.opportunity.stage_changed` (`OpportunityStageChanged`)
- `crm.activity.logged` (`ActivityLogged`)
- `crm.campaign.launched` (`CampaignLaunched`)

## 8. Finance Domain Events
- `finance.journal.created` (`JournalCreated`)
- `finance.journal.posted` (`JournalPosted`)
- `finance.invoice.posted` (`InvoicePosted`)
- `finance.bill.posted` (`BillPosted`)
- `finance.payment.recorded` (`PaymentRecorded`)
- `finance.period.closed` (`FiscalPeriodClosed`)

## 9. Reporting & BI Domain Events
- `reporting.report.generated` (`ReportGenerated`)
- `reporting.dashboard.viewed` (`DashboardViewed`)
- `reporting.scheduled_report.completed` (`ScheduledReportCompleted`)
- `reporting.kpi.updated` (`KPIUpdated`)
- `reporting.analytics.calculated` (`AnalyticsCalculated`)

## 10. Integrations & Infrastructure Events
- `integration.apikey.created` (`ApiKeyCreated`)
- `integration.webhook.delivered` (`WebhookDelivered`)
- `integration.backup.completed` (`BackupCompleted`)
