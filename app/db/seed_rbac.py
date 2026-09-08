import logging
from typing import Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.repositories.rbac import permission_repository, role_permission_repository, role_repository
from app.schemas.rbac import PermissionCreate, RoleCreate

logger = logging.getLogger("app.db.seed")

DEFAULT_PERMISSIONS: List[Dict[str, str]] = [
    # System Admin
    {"name": "Full System Access", "code": "admin.full_access", "description": "Full administrative control over all modules", "module_name": "admin"},
    
    # Users & Roles
    {"name": "Create Users", "code": "users.create", "description": "Permission to register and create new users", "module_name": "users"},
    {"name": "Read Users", "code": "users.read", "description": "Permission to view user accounts", "module_name": "users"},
    {"name": "Update Users", "code": "users.update", "description": "Permission to modify user accounts", "module_name": "users"},
    {"name": "Delete Users", "code": "users.delete", "description": "Permission to delete user accounts", "module_name": "users"},

    {"name": "Read Roles", "code": "roles.read", "description": "Permission to view roles and permissions", "module_name": "admin"},
    {"name": "Create Roles", "code": "roles.create", "description": "Permission to create security roles", "module_name": "admin"},
    {"name": "Update Roles", "code": "roles.update", "description": "Permission to modify security roles", "module_name": "admin"},
    {"name": "Delete Roles", "code": "roles.delete", "description": "Permission to delete security roles", "module_name": "admin"},

    # Employee Module Permissions
    {"name": "Create Employee", "code": "employee.create", "description": "Permission to create employee records", "module_name": "hr"},
    {"name": "Read Employee", "code": "employee.read", "description": "Permission to view employee records", "module_name": "hr"},
    {"name": "Update Employee", "code": "employee.update", "description": "Permission to update employee records", "module_name": "hr"},
    {"name": "Delete Employee", "code": "employee.delete", "description": "Permission to remove employee records", "module_name": "hr"},
    {"name": "Restore Employee", "code": "employee.restore", "description": "Permission to restore deleted employee records", "module_name": "hr"},

    # Employee Document Permissions
    {"name": "Create Employee Document", "code": "employee_document.create", "description": "Permission to upload/link employee documents", "module_name": "hr"},
    {"name": "Read Employee Document", "code": "employee_document.read", "description": "Permission to view employee documents", "module_name": "hr"},
    {"name": "Update Employee Document", "code": "employee_document.update", "description": "Permission to update employee document details", "module_name": "hr"},
    {"name": "Delete Employee Document", "code": "employee_document.delete", "description": "Permission to delete employee documents", "module_name": "hr"},
    {"name": "Verify Employee Document", "code": "employee_document.verify", "description": "Permission to verify or reject employee documents", "module_name": "hr"},
    {"name": "Restore Employee Document", "code": "employee_document.restore", "description": "Permission to restore deleted employee documents", "module_name": "hr"},

    # Position Management Permissions
    {"name": "Create Position", "code": "position.create", "description": "Permission to create job position definitions", "module_name": "hr"},
    {"name": "Read Position", "code": "position.read", "description": "Permission to view job position definitions", "module_name": "hr"},
    {"name": "Update Position", "code": "position.update", "description": "Permission to update job position definitions", "module_name": "hr"},
    {"name": "Delete Position", "code": "position.delete", "description": "Permission to remove job position definitions", "module_name": "hr"},
    {"name": "Restore Position", "code": "position.restore", "description": "Permission to restore soft-deleted job positions", "module_name": "hr"},

    # Shift Management Permissions
    {"name": "Create Shift", "code": "shift.create", "description": "Permission to create reusable shift schedules", "module_name": "hr"},
    {"name": "Read Shift", "code": "shift.read", "description": "Permission to view reusable shift schedules", "module_name": "hr"},
    {"name": "Update Shift", "code": "shift.update", "description": "Permission to update reusable shift schedules", "module_name": "hr"},
    {"name": "Delete Shift", "code": "shift.delete", "description": "Permission to remove reusable shift schedules", "module_name": "hr"},
    {"name": "Restore Shift", "code": "shift.restore", "description": "Permission to restore soft-deleted shift schedules", "module_name": "hr"},

    # Holiday Calendar Permissions
    {"name": "Create Holiday", "code": "holiday.create", "description": "Permission to create official holiday calendar entries", "module_name": "hr"},
    {"name": "Read Holiday", "code": "holiday.read", "description": "Permission to view official holiday calendar entries", "module_name": "hr"},
    {"name": "Update Holiday", "code": "holiday.update", "description": "Permission to update official holiday calendar entries", "module_name": "hr"},
    {"name": "Delete Holiday", "code": "holiday.delete", "description": "Permission to remove official holiday calendar entries", "module_name": "hr"},
    {"name": "Restore Holiday", "code": "holiday.restore", "description": "Permission to restore soft-deleted holiday calendar entries", "module_name": "hr"},

    # Attendance Engine Permissions
    {"name": "Read Attendance", "code": "attendance.read", "description": "Permission to view employee attendance records", "module_name": "hr"},
    {"name": "Check-in Attendance", "code": "attendance.checkin", "description": "Permission to record employee check-in", "module_name": "hr"},
    {"name": "Check-out Attendance", "code": "attendance.checkout", "description": "Permission to record employee check-out", "module_name": "hr"},
    {"name": "Correct Attendance", "code": "attendance.correct", "description": "Permission to manually correct attendance records", "module_name": "hr"},
    {"name": "Lock Attendance", "code": "attendance.lock", "description": "Permission to lock attendance records for payroll", "module_name": "hr"},

    # Shift Assignment & Scheduling Permissions
    {"name": "Create Shift Assignment", "code": "shift_assignment.create", "description": "Permission to assign shift schedules to employees", "module_name": "hr"},
    {"name": "Read Shift Assignment", "code": "shift_assignment.read", "description": "Permission to view employee shift assignments", "module_name": "hr"},
    {"name": "Update Shift Assignment", "code": "shift_assignment.update", "description": "Permission to update employee shift assignments", "module_name": "hr"},
    {"name": "Delete Shift Assignment", "code": "shift_assignment.delete", "description": "Permission to remove employee shift assignments", "module_name": "hr"},

    # Leave Types & Policies Permissions
    {"name": "Create Leave Type", "code": "leave_type.create", "description": "Permission to create organizational leave types and policies", "module_name": "hr"},
    {"name": "Read Leave Type", "code": "leave_type.read", "description": "Permission to view organizational leave types and policies", "module_name": "hr"},
    {"name": "Update Leave Type", "code": "leave_type.update", "description": "Permission to update organizational leave types and policies", "module_name": "hr"},
    {"name": "Delete Leave Type", "code": "leave_type.delete", "description": "Permission to remove organizational leave types and policies", "module_name": "hr"},
    {"name": "Restore Leave Type", "code": "leave_type.restore", "description": "Permission to restore soft-deleted leave types and policies", "module_name": "hr"},

    # Leave Balance Management Permissions
    {"name": "Create Leave Balance", "code": "leave_balance.create", "description": "Permission to initialize employee leave balances", "module_name": "hr"},
    {"name": "Read Leave Balance", "code": "leave_balance.read", "description": "Permission to view employee leave balances", "module_name": "hr"},
    {"name": "Update Leave Balance", "code": "leave_balance.update", "description": "Permission to update employee leave balances", "module_name": "hr"},
    {"name": "Adjust Leave Balance", "code": "leave_balance.adjust", "description": "Permission to manually adjust employee leave balances", "module_name": "hr"},
    {"name": "Delete Leave Balance", "code": "leave_balance.delete", "description": "Permission to remove employee leave balances", "module_name": "hr"},
    {"name": "Restore Leave Balance", "code": "leave_balance.restore", "description": "Permission to restore soft-deleted leave balances", "module_name": "hr"},

    # Leave Request Workflow Permissions
    {"name": "Create Leave Request", "code": "leave_request.create", "description": "Permission to create leave request applications", "module_name": "hr"},
    {"name": "Read Leave Request", "code": "leave_request.read", "description": "Permission to view leave request applications", "module_name": "hr"},
    {"name": "Submit Leave Request", "code": "leave_request.submit", "description": "Permission to submit leave requests for approval", "module_name": "hr"},
    {"name": "Approve Leave Request", "code": "leave_request.approve", "description": "Permission to approve employee leave requests", "module_name": "hr"},
    {"name": "Reject Leave Request", "code": "leave_request.reject", "description": "Permission to reject employee leave requests", "module_name": "hr"},
    {"name": "Cancel Leave Request", "code": "leave_request.cancel", "description": "Permission to cancel leave request applications", "module_name": "hr"},

    # Platform Approval Engine Permissions
    {"name": "Create Workflow Definition", "code": "workflow.create", "description": "Permission to create approval workflow definitions", "module_name": "platform"},
    {"name": "Read Workflow Definition", "code": "workflow.read", "description": "Permission to view approval workflow definitions", "module_name": "platform"},
    {"name": "Update Workflow Definition", "code": "workflow.update", "description": "Permission to update approval workflow definitions", "module_name": "platform"},
    {"name": "Delete Workflow Definition", "code": "workflow.delete", "description": "Permission to delete approval workflow definitions", "module_name": "platform"},
    {"name": "Read Approval Request", "code": "approval.read", "description": "Permission to view approval requests and histories", "module_name": "platform"},
    {"name": "Approve Approval Step", "code": "approval.approve", "description": "Permission to approve steps in approval requests", "module_name": "platform"},
    {"name": "Reject Approval Step", "code": "approval.reject", "description": "Permission to reject approval requests", "module_name": "platform"},

    # Enterprise Salary Component Permissions
    {"name": "Create Salary Component", "code": "salary_component.create", "description": "Permission to create salary component definitions", "module_name": "payroll"},
    {"name": "Read Salary Component", "code": "salary_component.read", "description": "Permission to view salary component definitions", "module_name": "payroll"},
    {"name": "Update Salary Component", "code": "salary_component.update", "description": "Permission to update salary component definitions", "module_name": "payroll"},
    {"name": "Delete Salary Component", "code": "salary_component.delete", "description": "Permission to delete salary component definitions", "module_name": "payroll"},
    {"name": "Restore Salary Component", "code": "salary_component.restore", "description": "Permission to restore deleted salary components", "module_name": "payroll"},

    # Enterprise Salary Structure Permissions
    {"name": "Create Salary Structure", "code": "salary_structure.create", "description": "Permission to create salary structure templates", "module_name": "payroll"},
    {"name": "Read Salary Structure", "code": "salary_structure.read", "description": "Permission to view salary structure templates", "module_name": "payroll"},
    {"name": "Update Salary Structure", "code": "salary_structure.update", "description": "Permission to update salary structure templates", "module_name": "payroll"},
    {"name": "Delete Salary Structure", "code": "salary_structure.delete", "description": "Permission to delete salary structure templates", "module_name": "payroll"},
    {"name": "Restore Salary Structure", "code": "salary_structure.restore", "description": "Permission to restore deleted salary structure templates", "module_name": "payroll"},

    # Employee Compensation Management Permissions
    {"name": "Create Compensation", "code": "compensation.create", "description": "Permission to assign or revise employee compensation", "module_name": "payroll"},
    {"name": "Read Compensation", "code": "compensation.read", "description": "Permission to view employee compensation records and history", "module_name": "payroll"},
    {"name": "Update Compensation", "code": "compensation.update", "description": "Permission to update employee compensation drafts", "module_name": "payroll"},
    {"name": "Activate Compensation", "code": "compensation.activate", "description": "Permission to activate employee compensation policies", "module_name": "payroll"},
    {"name": "Cancel Compensation", "code": "compensation.cancel", "description": "Permission to cancel employee compensation policies", "module_name": "payroll"},
    {"name": "Delete Compensation", "code": "compensation.delete", "description": "Permission to delete employee compensation records", "module_name": "payroll"},

    # Enterprise Payroll Processing Engine Permissions
    {"name": "Generate Payroll", "code": "payroll.generate", "description": "Permission to create periods and generate employee payroll runs", "module_name": "payroll"},
    {"name": "Read Payroll", "code": "payroll.read", "description": "Permission to view payroll periods and generated records", "module_name": "payroll"},
    {"name": "Approve Payroll", "code": "payroll.approve", "description": "Permission to approve calculated payroll records", "module_name": "payroll"},
    {"name": "Lock Payroll", "code": "payroll.lock", "description": "Permission to lock payroll periods against further changes", "module_name": "payroll"},

    # Enterprise Payroll Runs & Payslip Permissions
    {"name": "Create Payroll Run", "code": "payroll_run.create", "description": "Permission to create payroll run batches", "module_name": "payroll"},
    {"name": "Read Payroll Run", "code": "payroll_run.read", "description": "Permission to view payroll run batches", "module_name": "payroll"},
    {"name": "Update Payroll Run", "code": "payroll_run.update", "description": "Permission to start and complete payroll runs", "module_name": "payroll"},
    {"name": "Lock Payroll Run", "code": "payroll_run.lock", "description": "Permission to lock payroll run batches", "module_name": "payroll"},
    {"name": "Generate Payslip", "code": "payslip.generate", "description": "Permission to generate ReportLab PDF payslips", "module_name": "payroll"},
    {"name": "Publish Payslip", "code": "payslip.publish", "description": "Permission to publish generated payslips to employees", "module_name": "payroll"},
    {"name": "Read Payslip", "code": "payslip.read", "description": "Permission to view and download payslip documents", "module_name": "payroll"},

    # Statutory Compliance Engine Permissions
    {"name": "Create Country", "code": "country.create", "description": "Permission to create countries", "module_name": "payroll"},
    {"name": "Read Country", "code": "country.read", "description": "Permission to view countries", "module_name": "payroll"},
    {"name": "Update Country", "code": "country.update", "description": "Permission to update countries", "module_name": "payroll"},
    {"name": "Delete Country", "code": "country.delete", "description": "Permission to delete countries", "module_name": "payroll"},
    {"name": "Create Statutory Rule", "code": "statutory_rule.create", "description": "Permission to create statutory rules", "module_name": "payroll"},
    {"name": "Read Statutory Rule", "code": "statutory_rule.read", "description": "Permission to view statutory rules", "module_name": "payroll"},
    {"name": "Update Statutory Rule", "code": "statutory_rule.update", "description": "Permission to update statutory rules", "module_name": "payroll"},
    {"name": "Delete Statutory Rule", "code": "statutory_rule.delete", "description": "Permission to delete statutory rules", "module_name": "payroll"},
    {"name": "Create Statutory Profile", "code": "statutory_profile.create", "description": "Permission to assign employee statutory profiles", "module_name": "payroll"},
    {"name": "Read Statutory Profile", "code": "statutory_profile.read", "description": "Permission to view employee statutory profiles", "module_name": "payroll"},
    {"name": "Update Statutory Profile", "code": "statutory_profile.update", "description": "Permission to update employee statutory profiles", "module_name": "payroll"},

    # Payroll Finalization Suite Permissions
    {"name": "Create Payroll Adjustment", "code": "payroll.adjustment.create", "description": "Permission to create payroll adjustments", "module_name": "payroll"},
    {"name": "Update Payroll Adjustment", "code": "payroll.adjustment.update", "description": "Permission to update payroll adjustments", "module_name": "payroll"},
    {"name": "Delete Payroll Adjustment", "code": "payroll.adjustment.delete", "description": "Permission to delete payroll adjustments", "module_name": "payroll"},
    {"name": "Generate Payroll Report", "code": "payroll.report.generate", "description": "Permission to generate payroll report snapshots", "module_name": "payroll"},
    {"name": "Read Payroll Analytics", "code": "payroll.analytics.read", "description": "Permission to view payroll analytics dashboard", "module_name": "payroll"},
    {"name": "Export Bank Payment File", "code": "payroll.bank.export", "description": "Permission to generate bank payment CSV exports", "module_name": "payroll"},
    {"name": "Close Payroll Period", "code": "payroll.close", "description": "Permission to close completed payroll periods", "module_name": "payroll"},
    {"name": "Reopen Payroll Period", "code": "payroll.reopen", "description": "Permission to reopen closed payroll periods", "module_name": "payroll"},
    {"name": "Archive Payroll Period", "code": "payroll.archive", "description": "Permission to archive closed payroll periods", "module_name": "payroll"},
    {"name": "Publish Financial Payload", "code": "payroll.financial.publish", "description": "Permission to publish financial posting queue payloads", "module_name": "payroll"},


    # HR Configuration & Organization Policy Permissions
    {"name": "Read HR Configuration", "code": "hr_configuration.read", "description": "Permission to view organization HR policies", "module_name": "hr"},
    {"name": "Create HR Configuration", "code": "hr_configuration.create", "description": "Permission to create organization HR policies", "module_name": "hr"},
    {"name": "Update HR Configuration", "code": "hr_configuration.update", "description": "Permission to update organization HR policies", "module_name": "hr"},
    {"name": "Activate HR Configuration", "code": "hr_configuration.activate", "description": "Permission to activate organization HR policies", "module_name": "hr"},
    {"name": "Delete HR Configuration", "code": "hr_configuration.delete", "description": "Permission to delete organization HR policies", "module_name": "hr"},
    {"name": "Restore HR Configuration", "code": "hr_configuration.restore", "description": "Permission to restore deleted organization HR policies", "module_name": "hr"},

    # Departments
    {"name": "Create Department", "code": "department.create", "description": "Permission to create departments", "module_name": "hr"},
    {"name": "Read Department", "code": "department.read", "description": "Permission to view departments", "module_name": "hr"},
    {"name": "Update Department", "code": "department.update", "description": "Permission to update departments", "module_name": "hr"},
    {"name": "Delete Department", "code": "department.delete", "description": "Permission to remove departments", "module_name": "hr"},
    {"name": "Restore Department", "code": "department.restore", "description": "Permission to restore deleted departments", "module_name": "hr"},

    # Inventory Foundation Permissions
    {"name": "Create Category", "code": "inventory.category.create", "description": "Permission to create product categories", "module_name": "inventory"},
    {"name": "Read Category", "code": "inventory.category.read", "description": "Permission to view product categories", "module_name": "inventory"},
    {"name": "Update Category", "code": "inventory.category.update", "description": "Permission to update product categories", "module_name": "inventory"},
    {"name": "Delete Category", "code": "inventory.category.delete", "description": "Permission to delete product categories", "module_name": "inventory"},

    {"name": "Create Unit of Measure", "code": "inventory.unit.create", "description": "Permission to create units of measure", "module_name": "inventory"},
    {"name": "Read Unit of Measure", "code": "inventory.unit.read", "description": "Permission to view units of measure", "module_name": "inventory"},
    {"name": "Update Unit of Measure", "code": "inventory.unit.update", "description": "Permission to update units of measure", "module_name": "inventory"},
    {"name": "Delete Unit of Measure", "code": "inventory.unit.delete", "description": "Permission to delete units of measure", "module_name": "inventory"},

    {"name": "Create UOM", "code": "inventory.uom.create", "description": "Permission to create units of measure", "module_name": "inventory"},
    {"name": "Read UOM", "code": "inventory.uom.read", "description": "Permission to view units of measure", "module_name": "inventory"},
    {"name": "Update UOM", "code": "inventory.uom.update", "description": "Permission to update units of measure", "module_name": "inventory"},
    {"name": "Delete UOM", "code": "inventory.uom.delete", "description": "Permission to delete units of measure", "module_name": "inventory"},

    {"name": "Create Brand", "code": "inventory.brand.create", "description": "Permission to create product brands", "module_name": "inventory"},
    {"name": "Read Brand", "code": "inventory.brand.read", "description": "Permission to view product brands", "module_name": "inventory"},
    {"name": "Update Brand", "code": "inventory.brand.update", "description": "Permission to update product brands", "module_name": "inventory"},
    {"name": "Delete Brand", "code": "inventory.brand.delete", "description": "Permission to delete product brands", "module_name": "inventory"},

    {"name": "Create Warehouse", "code": "inventory.warehouse.create", "description": "Permission to create warehouse facilities", "module_name": "inventory"},
    {"name": "Read Warehouse", "code": "inventory.warehouse.read", "description": "Permission to view warehouse facilities", "module_name": "inventory"},
    {"name": "Update Warehouse", "code": "inventory.warehouse.update", "description": "Permission to update warehouse facilities", "module_name": "inventory"},
    {"name": "Delete Warehouse", "code": "inventory.warehouse.delete", "description": "Permission to delete warehouse facilities", "module_name": "inventory"},

    {"name": "Create Storage Location", "code": "inventory.location.create", "description": "Permission to create storage locations", "module_name": "inventory"},
    {"name": "Read Storage Location", "code": "inventory.location.read", "description": "Permission to view storage locations", "module_name": "inventory"},
    {"name": "Update Storage Location", "code": "inventory.location.update", "description": "Permission to update storage locations", "module_name": "inventory"},
    {"name": "Delete Storage Location", "code": "inventory.location.delete", "description": "Permission to delete storage locations", "module_name": "inventory"},

    {"name": "Create Product", "code": "inventory.product.create", "description": "Permission to create products in product master", "module_name": "inventory"},
    {"name": "Read Product", "code": "inventory.product.read", "description": "Permission to view products in product master", "module_name": "inventory"},
    {"name": "Update Product", "code": "inventory.product.update", "description": "Permission to update products in product master", "module_name": "inventory"},
    {"name": "Delete Product", "code": "inventory.product.delete", "description": "Permission to delete products in product master", "module_name": "inventory"},

    {"name": "Create Product Warehouse Configuration", "code": "inventory.product_warehouse.create", "description": "Permission to configure product warehouse parameters", "module_name": "inventory"},
    {"name": "Read Product Warehouse Configuration", "code": "inventory.product_warehouse.read", "description": "Permission to view product warehouse configurations", "module_name": "inventory"},
    {"name": "Update Product Warehouse Configuration", "code": "inventory.product_warehouse.update", "description": "Permission to update product warehouse parameters", "module_name": "inventory"},
    {"name": "Delete Product Warehouse Configuration", "code": "inventory.product_warehouse.delete", "description": "Permission to delete product warehouse parameters", "module_name": "inventory"},

    {"name": "Read Inventory Policy", "code": "inventory.policy.read", "description": "Permission to view inventory policies", "module_name": "inventory"},
    {"name": "Update Inventory Policy", "code": "inventory.policy.update", "description": "Permission to configure inventory policies", "module_name": "inventory"},

    {"name": "Create Product Attribute", "code": "inventory.attribute.create", "description": "Permission to create product attributes", "module_name": "inventory"},
    {"name": "Read Product Attribute", "code": "inventory.attribute.read", "description": "Permission to view product attributes", "module_name": "inventory"},
    {"name": "Update Product Attribute", "code": "inventory.attribute.update", "description": "Permission to update product attributes", "module_name": "inventory"},
    {"name": "Delete Product Attribute", "code": "inventory.attribute.delete", "description": "Permission to delete product attributes", "module_name": "inventory"},

    {"name": "Upload Product Document", "code": "inventory.document.upload", "description": "Permission to upload product documents", "module_name": "inventory"},
    {"name": "Read Product Document", "code": "inventory.document.read", "description": "Permission to view product documents", "module_name": "inventory"},
    {"name": "Delete Product Document", "code": "inventory.document.delete", "description": "Permission to delete product documents", "module_name": "inventory"},

    # Stock Engine Permissions
    {"name": "Read Transaction Types", "code": "inventory.transaction.read", "description": "Permission to view inventory transaction types", "module_name": "inventory"},
    {"name": "Read Stock Ledger", "code": "inventory.ledger.read", "description": "Permission to view stock ledger entries", "module_name": "inventory"},
    {"name": "Read Stock Balances", "code": "inventory.balance.read", "description": "Permission to view current stock balances and projections", "module_name": "inventory"},
    {"name": "Read Stock", "code": "inventory.stock.read", "description": "Permission to view stock queries and balances", "module_name": "inventory"},
    {"name": "Create Stock Movement", "code": "inventory.stock.movement.create", "description": "Permission to create stock IN/OUT/Adjustment movements", "module_name": "inventory"},
    {"name": "Read Stock Ledger v2", "code": "inventory.stock.ledger.read", "description": "Permission to view stock ledger entries", "module_name": "inventory"},
    {"name": "Read Stock Balance v2", "code": "inventory.stock.balance.read", "description": "Permission to view current stock balances", "module_name": "inventory"},
    {"name": "Create Opening Stock", "code": "inventory.opening.create", "description": "Permission to create opening stock initialization records", "module_name": "inventory"},
    {"name": "Create Inventory Adjustment", "code": "inventory.adjustment.create", "description": "Permission to create inventory adjustment proposals", "module_name": "inventory"},
    {"name": "Approve Inventory Adjustment", "code": "inventory.adjustment.approve", "description": "Permission to approve inventory adjustment proposals", "module_name": "inventory"},
    {"name": "Apply Inventory Adjustment", "code": "inventory.adjustment.apply", "description": "Permission to apply approved inventory adjustments to stock ledger", "module_name": "inventory"},


    # Warehouse Operations Engine Permissions
    {"name": "Create Goods Receipt", "code": "inventory.receipt.create", "description": "Permission to create goods receipt documents", "module_name": "inventory"},
    {"name": "Read Goods Receipt", "code": "inventory.receipt.read", "description": "Permission to view goods receipt documents", "module_name": "inventory"},
    {"name": "Update Goods Receipt", "code": "inventory.receipt.update", "description": "Permission to modify draft goods receipt documents", "module_name": "inventory"},
    {"name": "Delete Goods Receipt", "code": "inventory.receipt.delete", "description": "Permission to delete draft goods receipt documents", "module_name": "inventory"},
    {"name": "Approve Goods Receipt", "code": "inventory.receipt.approve", "description": "Permission to approve goods receipt documents", "module_name": "inventory"},
    {"name": "Post Goods Receipt", "code": "inventory.receipt.post", "description": "Permission to post goods receipt and generate stock ledger entries", "module_name": "inventory"},
    {"name": "Receive Goods Receipt", "code": "inventory.receipt.receive", "description": "Permission to receive goods receipt and generate stock ledger entries", "module_name": "inventory"},
    {"name": "Cancel Goods Receipt", "code": "inventory.receipt.cancel", "description": "Permission to cancel goods receipt documents", "module_name": "inventory"},

    {"name": "Create Goods Issue", "code": "inventory.issue.create", "description": "Permission to create goods issue documents", "module_name": "inventory"},
    {"name": "Read Goods Issue", "code": "inventory.issue.read", "description": "Permission to view goods issue documents", "module_name": "inventory"},
    {"name": "Update Goods Issue", "code": "inventory.issue.update", "description": "Permission to modify draft goods issue documents", "module_name": "inventory"},
    {"name": "Delete Goods Issue", "code": "inventory.issue.delete", "description": "Permission to delete draft goods issue documents", "module_name": "inventory"},
    {"name": "Approve Goods Issue", "code": "inventory.issue.approve", "description": "Permission to approve goods issue documents", "module_name": "inventory"},
    {"name": "Post Goods Issue", "code": "inventory.issue.post", "description": "Permission to post goods issue and generate stock ledger OUT entries", "module_name": "inventory"},
    {"name": "Issue Goods Issue", "code": "inventory.issue.issue", "description": "Permission to issue goods issue and generate stock ledger OUT entries", "module_name": "inventory"},
    {"name": "Cancel Goods Issue", "code": "inventory.issue.cancel", "description": "Permission to cancel goods issue documents", "module_name": "inventory"},

    {"name": "Create Stock Transfer", "code": "inventory.transfer.create", "description": "Permission to create stock transfer proposals", "module_name": "inventory"},
    {"name": "Read Stock Transfer", "code": "inventory.transfer.read", "description": "Permission to view stock transfer documents", "module_name": "inventory"},
    {"name": "Update Stock Transfer", "code": "inventory.transfer.update", "description": "Permission to modify draft stock transfer documents", "module_name": "inventory"},
    {"name": "Delete Stock Transfer", "code": "inventory.transfer.delete", "description": "Permission to delete draft stock transfer documents", "module_name": "inventory"},
    {"name": "Approve Stock Transfer", "code": "inventory.transfer.approve", "description": "Permission to approve stock transfer proposals", "module_name": "inventory"},
    {"name": "Post Stock Transfer", "code": "inventory.transfer.post", "description": "Permission to post atomic stock transfer and update stock balances", "module_name": "inventory"},
    {"name": "Dispatch Stock Transfer", "code": "inventory.transfer.dispatch", "description": "Permission to dispatch stock transfer out of source warehouse", "module_name": "inventory"},
    {"name": "Receive Stock Transfer", "code": "inventory.transfer.receive", "description": "Permission to receive stock transfer at destination warehouse", "module_name": "inventory"},
    {"name": "Complete Stock Transfer", "code": "inventory.transfer.complete", "description": "Permission to complete stock transfer and finalize stock ledger entries", "module_name": "inventory"},
    {"name": "Cancel Stock Transfer", "code": "inventory.transfer.cancel", "description": "Permission to cancel stock transfer documents", "module_name": "inventory"},

    {"name": "Execute Warehouse Operation", "code": "inventory.execute.warehouse", "description": "Permission to execute warehouse operations", "module_name": "inventory"},

    # Inventory Advanced Domain Completion Permissions
    {"name": "Create Batch", "code": "inventory.batch.create", "description": "Permission to create product batches", "module_name": "inventory"},
    {"name": "Read Batch", "code": "inventory.batch.read", "description": "Permission to view product batches", "module_name": "inventory"},
    {"name": "Update Batch", "code": "inventory.batch.update", "description": "Permission to update product batches", "module_name": "inventory"},
    {"name": "Delete Batch", "code": "inventory.batch.delete", "description": "Permission to delete product batches", "module_name": "inventory"},

    {"name": "Create Serial Number", "code": "inventory.serial.create", "description": "Permission to register serial numbers", "module_name": "inventory"},
    {"name": "Read Serial Number", "code": "inventory.serial.read", "description": "Permission to view serial numbers", "module_name": "inventory"},
    {"name": "Update Serial Number", "code": "inventory.serial.update", "description": "Permission to update serial number status and location", "module_name": "inventory"},

    {"name": "Create Lot", "code": "inventory.lot.create", "description": "Permission to create production lots", "module_name": "inventory"},
    {"name": "Read Lot", "code": "inventory.lot.read", "description": "Permission to view production lots", "module_name": "inventory"},

    {"name": "Create Stock Reservation", "code": "inventory.reservation.create", "description": "Permission to reserve stock", "module_name": "inventory"},
    {"name": "Read Stock Reservation", "code": "inventory.reservation.read", "description": "Permission to view stock reservations", "module_name": "inventory"},
    {"name": "Release Stock Reservation", "code": "inventory.reservation.release", "description": "Permission to release active stock reservations", "module_name": "inventory"},
    {"name": "Consume Stock Reservation", "code": "inventory.reservation.consume", "description": "Permission to consume active stock reservations", "module_name": "inventory"},
    {"name": "Cancel Stock Reservation", "code": "inventory.reservation.cancel", "description": "Permission to cancel stock reservations", "module_name": "inventory"},

    {"name": "Create Cycle Count", "code": "inventory.cycle_count.create", "description": "Permission to create cycle count documents", "module_name": "inventory"},
    {"name": "Read Cycle Count", "code": "inventory.cycle_count.read", "description": "Permission to view cycle count documents", "module_name": "inventory"},
    {"name": "Approve Cycle Count", "code": "inventory.cycle_count.approve", "description": "Permission to approve cycle count and trigger stock adjustment", "module_name": "inventory"},
    {"name": "Read Inventory Reports", "code": "inventory.reports.read", "description": "Permission to view inventory reports", "module_name": "inventory"},
    {"name": "Read Inventory Stock Report", "code": "inventory.report.stock.read", "description": "Permission to view current stock and availability reports", "module_name": "inventory"},
    {"name": "Read Inventory Movement Report", "code": "inventory.report.movement.read", "description": "Permission to view stock movement reports", "module_name": "inventory"},
    {"name": "Read Inventory Warehouse Report", "code": "inventory.report.warehouse.read", "description": "Permission to view warehouse inventory reports", "module_name": "inventory"},
    {"name": "Read Inventory Product Report", "code": "inventory.report.product.read", "description": "Permission to view product inventory reports", "module_name": "inventory"},
    {"name": "Read Inventory Batch Report", "code": "inventory.report.batch.read", "description": "Permission to view batch and expiry reports", "module_name": "inventory"},
    {"name": "Read Inventory Serial Report", "code": "inventory.report.serial.read", "description": "Permission to view serial inventory reports", "module_name": "inventory"},
    {"name": "Read Inventory Reservation Report", "code": "inventory.report.reservation.read", "description": "Permission to view stock reservation reports", "module_name": "inventory"},
    {"name": "Read Inventory Analytics Report", "code": "inventory.report.analytics.read", "description": "Permission to view inventory analytics and movement trends", "module_name": "inventory"},
    {"name": "Export Inventory Reports", "code": "inventory.report.export", "description": "Permission to export inventory reports to CSV", "module_name": "inventory"},
    {"name": "Read Inventory Analytics", "code": "inventory.analytics.read", "description": "Permission to view inventory analytics and dashboard", "module_name": "inventory"},
    {"name": "Execute Import Export", "code": "inventory.import_export.execute", "description": "Permission to import and export inventory data", "module_name": "inventory"},

    # Procurement Domain Completion Permissions
    {"name": "Create Supplier", "code": "procurement.supplier.create", "description": "Permission to create suppliers", "module_name": "procurement"},
    {"name": "Read Supplier", "code": "procurement.supplier.read", "description": "Permission to view suppliers", "module_name": "procurement"},
    {"name": "Update Supplier", "code": "procurement.supplier.update", "description": "Permission to update suppliers", "module_name": "procurement"},
    {"name": "Delete Supplier", "code": "procurement.supplier.delete", "description": "Permission to delete suppliers", "module_name": "procurement"},
    {"name": "Blacklist Supplier", "code": "procurement.supplier.blacklist", "description": "Permission to blacklist suppliers", "module_name": "procurement"},

    {"name": "Create Supplier Category", "code": "procurement.category.create", "description": "Permission to create supplier categories", "module_name": "procurement"},
    {"name": "Read Supplier Category", "code": "procurement.category.read", "description": "Permission to view supplier categories", "module_name": "procurement"},
    {"name": "Update Supplier Category", "code": "procurement.category.update", "description": "Permission to update supplier categories", "module_name": "procurement"},
    {"name": "Delete Supplier Category", "code": "procurement.category.delete", "description": "Permission to delete supplier categories", "module_name": "procurement"},

    {"name": "Create Supplier Contact", "code": "procurement.contact.create", "description": "Permission to create supplier contacts", "module_name": "procurement"},
    {"name": "Read Supplier Contact", "code": "procurement.contact.read", "description": "Permission to view supplier contacts", "module_name": "procurement"},
    {"name": "Update Supplier Contact", "code": "procurement.contact.update", "description": "Permission to update supplier contacts", "module_name": "procurement"},
    {"name": "Delete Supplier Contact", "code": "procurement.contact.delete", "description": "Permission to delete supplier contacts", "module_name": "procurement"},

    {"name": "Create Supplier Address", "code": "procurement.address.create", "description": "Permission to create supplier addresses", "module_name": "procurement"},
    {"name": "Read Supplier Address", "code": "procurement.address.read", "description": "Permission to view supplier addresses", "module_name": "procurement"},
    {"name": "Update Supplier Address", "code": "procurement.address.update", "description": "Permission to update supplier addresses", "module_name": "procurement"},
    {"name": "Delete Supplier Address", "code": "procurement.address.delete", "description": "Permission to delete supplier addresses", "module_name": "procurement"},

    {"name": "Create Supplier Document", "code": "procurement.document.create", "description": "Permission to attach supplier documents", "module_name": "procurement"},
    {"name": "Read Supplier Document", "code": "procurement.document.read", "description": "Permission to view supplier documents", "module_name": "procurement"},
    {"name": "Update Supplier Document", "code": "procurement.document.update", "description": "Permission to update supplier documents", "module_name": "procurement"},
    {"name": "Delete Supplier Document", "code": "procurement.document.delete", "description": "Permission to delete supplier documents", "module_name": "procurement"},

    {"name": "Create Supplier Rating", "code": "procurement.rating.create", "description": "Permission to evaluate and rate suppliers", "module_name": "procurement"},
    {"name": "Read Supplier Rating", "code": "procurement.rating.read", "description": "Permission to view supplier evaluations and ratings", "module_name": "procurement"},

    {"name": "Create Purchase Requisition", "code": "procurement.requisition.create", "description": "Permission to create purchase requisitions", "module_name": "procurement"},
    {"name": "Read Purchase Requisition", "code": "procurement.requisition.read", "description": "Permission to view purchase requisitions", "module_name": "procurement"},
    {"name": "Update Purchase Requisition", "code": "procurement.requisition.update", "description": "Permission to update purchase requisitions", "module_name": "procurement"},
    {"name": "Submit Purchase Requisition", "code": "procurement.requisition.submit", "description": "Permission to submit purchase requisitions", "module_name": "procurement"},
    {"name": "Approve Purchase Requisition", "code": "procurement.requisition.approve", "description": "Permission to approve purchase requisitions", "module_name": "procurement"},
    {"name": "Cancel Purchase Requisition", "code": "procurement.requisition.cancel", "description": "Permission to cancel purchase requisitions", "module_name": "procurement"},

    {"name": "Create RFQ", "code": "procurement.rfq.create", "description": "Permission to create requests for quotation", "module_name": "procurement"},
    {"name": "Read RFQ", "code": "procurement.rfq.read", "description": "Permission to view requests for quotation", "module_name": "procurement"},
    {"name": "Update RFQ", "code": "procurement.rfq.update", "description": "Permission to update requests for quotation", "module_name": "procurement"},
    {"name": "Issue RFQ", "code": "procurement.rfq.issue", "description": "Permission to issue requests for quotation to suppliers", "module_name": "procurement"},
    {"name": "Cancel RFQ", "code": "procurement.rfq.cancel", "description": "Permission to cancel requests for quotation", "module_name": "procurement"},

    {"name": "Create Supplier Quotation", "code": "procurement.quotation.create", "description": "Permission to create supplier quotations", "module_name": "procurement"},
    {"name": "Read Supplier Quotation", "code": "procurement.quotation.read", "description": "Permission to view supplier quotations", "module_name": "procurement"},
    {"name": "Update Supplier Quotation", "code": "procurement.quotation.update", "description": "Permission to update supplier quotations", "module_name": "procurement"},
    {"name": "Submit Supplier Quotation", "code": "procurement.quotation.submit", "description": "Permission to submit supplier quotations", "module_name": "procurement"},
    {"name": "Withdraw Supplier Quotation", "code": "procurement.quotation.withdraw", "description": "Permission to withdraw supplier quotations", "module_name": "procurement"},
    {"name": "Approve Supplier Quotation", "code": "procurement.quotation.approve", "description": "Permission to approve supplier quotations", "module_name": "procurement"},
    {"name": "Read Sourcing", "code": "procurement.sourcing.read", "description": "Permission to view sourcing activities", "module_name": "procurement"},
    {"name": "Compare Sourcing Quotations", "code": "procurement.sourcing.compare", "description": "Permission to compare supplier quotations in RFQ", "module_name": "procurement"},
    {"name": "Award Sourcing Quotation", "code": "procurement.quotation.award", "description": "Permission to award winning supplier quotation", "module_name": "procurement"},

    {"name": "Create Purchase Order", "code": "procurement.purchase_order.create", "description": "Permission to create purchase orders", "module_name": "procurement"},
    {"name": "Read Purchase Order", "code": "procurement.purchase_order.read", "description": "Permission to view purchase orders", "module_name": "procurement"},
    {"name": "Update Purchase Order", "code": "procurement.purchase_order.update", "description": "Permission to update purchase orders", "module_name": "procurement"},
    {"name": "Submit Purchase Order", "code": "procurement.purchase_order.submit", "description": "Permission to submit purchase orders for approval", "module_name": "procurement"},
    {"name": "Approve Purchase Order", "code": "procurement.purchase_order.approve", "description": "Permission to approve purchase orders", "module_name": "procurement"},
    {"name": "Amend Purchase Order", "code": "procurement.purchase_order.amend", "description": "Permission to amend approved purchase orders", "module_name": "procurement"},
    {"name": "Cancel Purchase Order", "code": "procurement.purchase_order.cancel", "description": "Permission to cancel purchase orders", "module_name": "procurement"},
    {"name": "Dispatch Purchase Order", "code": "procurement.purchase_order.dispatch", "description": "Permission to dispatch purchase orders to suppliers", "module_name": "procurement"},
    {"name": "Close Purchase Order", "code": "procurement.purchase_order.close", "description": "Permission to close purchase orders", "module_name": "procurement"},

    {"name": "Create Purchase Return", "code": "procurement.purchase_return.create", "description": "Permission to create purchase returns", "module_name": "procurement"},
    {"name": "Read Purchase Return", "code": "procurement.purchase_return.read", "description": "Permission to view purchase returns", "module_name": "procurement"},
    {"name": "Update Purchase Return", "code": "procurement.purchase_return.update", "description": "Permission to update draft purchase returns", "module_name": "procurement"},
    {"name": "Approve Purchase Return", "code": "procurement.purchase_return.approve", "description": "Permission to approve purchase returns", "module_name": "procurement"},
    {"name": "Post Purchase Return", "code": "procurement.purchase_return.post", "description": "Permission to post purchase returns and reverse stock", "module_name": "procurement"},
    {"name": "Cancel Purchase Return", "code": "procurement.purchase_return.cancel", "description": "Permission to cancel purchase returns", "module_name": "procurement"},

    {"name": "Read Receiving", "code": "procurement.receiving.read", "description": "Permission to view purchase receipts and receiving history", "module_name": "procurement"},
    {"name": "Create Receiving", "code": "procurement.receiving.create", "description": "Permission to initiate purchase order receiving", "module_name": "procurement"},
    {"name": "Post Receiving", "code": "procurement.receiving.post", "description": "Permission to post goods receipts and increment physical stock", "module_name": "procurement"},

    {"name": "Read Procurement Analytics", "code": "procurement.analytics.read", "description": "Permission to view procurement analytics and dashboard", "module_name": "procurement"},
    {"name": "Read Procurement Reports", "code": "procurement.reports.read", "description": "Permission to view procurement reports", "module_name": "procurement"},
    {"name": "Execute Procurement Import Export", "code": "procurement.import_export.execute", "description": "Permission to import and export procurement data", "module_name": "procurement"},

    # Sales Domain Completion Permissions
    {"name": "Create Customer", "code": "sales.customer.create", "description": "Permission to create customer master records", "module_name": "sales"},
    {"name": "Read Customer", "code": "sales.customer.read", "description": "Permission to view customer master records", "module_name": "sales"},
    {"name": "Update Customer", "code": "sales.customer.update", "description": "Permission to update customer master records", "module_name": "sales"},
    {"name": "Delete Customer", "code": "sales.customer.delete", "description": "Permission to delete customer master records", "module_name": "sales"},

    {"name": "Create Sales Quotation", "code": "sales.quotation.create", "description": "Permission to create sales quotations", "module_name": "sales"},
    {"name": "Read Sales Quotation", "code": "sales.quotation.read", "description": "Permission to view sales quotations", "module_name": "sales"},
    {"name": "Update Sales Quotation", "code": "sales.quotation.update", "description": "Permission to update sales quotations", "module_name": "sales"},
    {"name": "Submit Sales Quotation", "code": "sales.quotation.submit", "description": "Permission to submit sales quotations", "module_name": "sales"},
    {"name": "Approve Sales Quotation", "code": "sales.quotation.approve", "description": "Permission to approve or reject sales quotations", "module_name": "sales"},
    {"name": "Cancel Sales Quotation", "code": "sales.quotation.cancel", "description": "Permission to cancel sales quotations", "module_name": "sales"},

    {"name": "Create Sales Order", "code": "sales.order.create", "description": "Permission to create sales orders", "module_name": "sales"},
    {"name": "Read Sales Order", "code": "sales.order.read", "description": "Permission to view sales orders", "module_name": "sales"},
    {"name": "Update Sales Order", "code": "sales.order.update", "description": "Permission to update sales orders", "module_name": "sales"},
    {"name": "Submit Sales Order", "code": "sales.order.submit", "description": "Permission to submit sales orders for approval", "module_name": "sales"},
    {"name": "Approve Sales Order", "code": "sales.order.approve", "description": "Permission to approve or reject sales orders", "module_name": "sales"},
    {"name": "Cancel Sales Order", "code": "sales.order.cancel", "description": "Permission to cancel sales orders", "module_name": "sales"},
    {"name": "Fulfill Sales Order", "code": "sales.order.fulfill", "description": "Permission to fulfill sales orders", "module_name": "sales"},

    {"name": "Create Delivery Order", "code": "sales.delivery.create", "description": "Permission to create delivery orders and dispatches", "module_name": "sales"},
    {"name": "Read Delivery Order", "code": "sales.delivery.read", "description": "Permission to view delivery orders and tracking", "module_name": "sales"},
    {"name": "Update Delivery Order", "code": "sales.delivery.update", "description": "Permission to update delivery orders", "module_name": "sales"},

    {"name": "Create Sales Return", "code": "sales.return.create", "description": "Permission to create sales returns", "module_name": "sales"},
    {"name": "Read Sales Return", "code": "sales.return.read", "description": "Permission to view sales returns", "module_name": "sales"},
    {"name": "Approve Sales Return", "code": "sales.return.approve", "description": "Permission to approve and process sales returns", "module_name": "sales"},

    {"name": "Create Pricing Rules", "code": "sales.pricing.create", "description": "Permission to create price lists and discount rules", "module_name": "sales"},
    {"name": "Read Pricing Rules", "code": "sales.pricing.read", "description": "Permission to view price lists and discount rules", "module_name": "sales"},
    {"name": "Update Pricing Rules", "code": "sales.pricing.update", "description": "Permission to update price lists and discount rules", "module_name": "sales"},

    {"name": "Read Sales Analytics", "code": "sales.analytics.read", "description": "Permission to view sales analytics and reports", "module_name": "sales"},

    # CRM Domain Completion Permissions
    {"name": "Create Lead", "code": "crm.lead.create", "description": "Permission to create leads", "module_name": "crm"},
    {"name": "Read Lead", "code": "crm.lead.read", "description": "Permission to view leads", "module_name": "crm"},
    {"name": "Update Lead", "code": "crm.lead.update", "description": "Permission to update leads", "module_name": "crm"},
    {"name": "Delete Lead", "code": "crm.lead.delete", "description": "Permission to delete leads", "module_name": "crm"},
    {"name": "Convert Lead", "code": "crm.lead.convert", "description": "Permission to convert leads to opportunities and customers", "module_name": "crm"},

    {"name": "Create Opportunity", "code": "crm.opportunity.create", "description": "Permission to create opportunities", "module_name": "crm"},
    {"name": "Read Opportunity", "code": "crm.opportunity.read", "description": "Permission to view opportunities", "module_name": "crm"},
    {"name": "Update Opportunity", "code": "crm.opportunity.update", "description": "Permission to update opportunities", "module_name": "crm"},
    {"name": "Delete Opportunity", "code": "crm.opportunity.delete", "description": "Permission to delete opportunities", "module_name": "crm"},
    {"name": "Stage Opportunity", "code": "crm.opportunity.stage", "description": "Permission to advance/change opportunity pipeline stage", "module_name": "crm"},

    {"name": "Create Activity", "code": "crm.activity.create", "description": "Permission to log activities", "module_name": "crm"},
    {"name": "Read Activity", "code": "crm.activity.read", "description": "Permission to view activities", "module_name": "crm"},
    {"name": "Update Activity", "code": "crm.activity.update", "description": "Permission to update activities", "module_name": "crm"},
    {"name": "Delete Activity", "code": "crm.activity.delete", "description": "Permission to delete activities", "module_name": "crm"},

    {"name": "Create Meeting", "code": "crm.meeting.create", "description": "Permission to schedule meetings", "module_name": "crm"},
    {"name": "Read Meeting", "code": "crm.meeting.read", "description": "Permission to view meetings", "module_name": "crm"},
    {"name": "Update Meeting", "code": "crm.meeting.update", "description": "Permission to update meetings", "module_name": "crm"},

    {"name": "Create Task", "code": "crm.task.create", "description": "Permission to create CRM tasks", "module_name": "crm"},
    {"name": "Read Task", "code": "crm.task.read", "description": "Permission to view CRM tasks", "module_name": "crm"},
    {"name": "Update Task", "code": "crm.task.update", "description": "Permission to update CRM tasks", "module_name": "crm"},

    {"name": "Create Campaign", "code": "crm.campaign.create", "description": "Permission to create marketing campaigns", "module_name": "crm"},
    {"name": "Read Campaign", "code": "crm.campaign.read", "description": "Permission to view marketing campaigns", "module_name": "crm"},
    {"name": "Update Campaign", "code": "crm.campaign.update", "description": "Permission to update marketing campaigns", "module_name": "crm"},

    {"name": "Read CRM Analytics", "code": "crm.analytics.read", "description": "Permission to view CRM analytics and reports", "module_name": "crm"},
    {"name": "Search CRM", "code": "crm.search.read", "description": "Permission to execute global CRM searches", "module_name": "crm"},

    # Inventory
    {"name": "Create Inventory Items", "code": "inventory.create", "description": "Permission to add inventory stock", "module_name": "inventory"},
    {"name": "Read Inventory Items", "code": "inventory.read", "description": "Permission to view inventory stock", "module_name": "inventory"},
    {"name": "Update Inventory Items", "code": "inventory.update", "description": "Permission to modify inventory stock", "module_name": "inventory"},
    {"name": "Delete Inventory Items", "code": "inventory.delete", "description": "Permission to delete inventory stock", "module_name": "inventory"},

    # Finance Core Permissions
    {"name": "Create Company", "code": "finance.company.create", "description": "Permission to create legal entity company master", "module_name": "finance"},
    {"name": "Read Company", "code": "finance.company.read", "description": "Permission to view legal entity company master", "module_name": "finance"},
    {"name": "Update Company", "code": "finance.company.update", "description": "Permission to update legal entity company master", "module_name": "finance"},
    {"name": "Delete Company", "code": "finance.company.delete", "description": "Permission to delete legal entity company master", "module_name": "finance"},

    {"name": "Create Account", "code": "finance.accounts.create", "description": "Permission to create accounts and groups", "module_name": "finance"},
    {"name": "Read Account", "code": "finance.accounts.read", "description": "Permission to view chart of accounts", "module_name": "finance"},
    {"name": "Update Account", "code": "finance.accounts.update", "description": "Permission to update chart of accounts", "module_name": "finance"},
    {"name": "Delete Account", "code": "finance.accounts.delete", "description": "Permission to delete accounts", "module_name": "finance"},

    {"name": "Create Journal", "code": "finance.journal.create", "description": "Permission to create journal entries", "module_name": "finance"},
    {"name": "Read Journal", "code": "finance.journal.read", "description": "Permission to view journal entries", "module_name": "finance"},
    {"name": "Update Journal", "code": "finance.journal.update", "description": "Permission to update draft journal entries", "module_name": "finance"},
    {"name": "Delete Journal", "code": "finance.journal.delete", "description": "Permission to delete draft journal entries", "module_name": "finance"},
    {"name": "Post Journal", "code": "finance.journal.post", "description": "Permission to post journal entries to General Ledger", "module_name": "finance"},
    {"name": "Reverse Journal", "code": "finance.journal.reverse", "description": "Permission to reverse posted journal entries", "module_name": "finance"},
    {"name": "Cancel Journal", "code": "finance.journal.cancel", "description": "Permission to cancel draft journal entries", "module_name": "finance"},

    {"name": "Read General Ledger", "code": "finance.ledger.read", "description": "Permission to view general ledger transactions and account ledgers", "module_name": "finance"},
    {"name": "Read Financial Reports", "code": "finance.reports.read", "description": "Permission to view trial balance and financial reports", "module_name": "finance"},

    {"name": "Create Posting Rule", "code": "finance.posting.create", "description": "Permission to create posting rules", "module_name": "finance"},
    {"name": "Read Posting Rule", "code": "finance.posting.read", "description": "Permission to view posting rules", "module_name": "finance"},
    {"name": "Update Posting Rule", "code": "finance.posting.update", "description": "Permission to update posting rules", "module_name": "finance"},
    {"name": "Delete Posting Rule", "code": "finance.posting.delete", "description": "Permission to delete posting rules", "module_name": "finance"},

    {"name": "Create Tax", "code": "finance.tax.create", "description": "Permission to create tax categories and rates", "module_name": "finance"},
    {"name": "Read Tax", "code": "finance.tax.read", "description": "Permission to view tax categories and rates", "module_name": "finance"},
    {"name": "Update Tax", "code": "finance.tax.update", "description": "Permission to update tax categories and rates", "module_name": "finance"},
    {"name": "Delete Tax", "code": "finance.tax.delete", "description": "Permission to delete tax categories and rates", "module_name": "finance"},

    {"name": "Create Currency", "code": "finance.currency.create", "description": "Permission to create currencies and exchange rates", "module_name": "finance"},
    {"name": "Read Currency", "code": "finance.currency.read", "description": "Permission to view currencies and exchange rates", "module_name": "finance"},
    {"name": "Update Currency", "code": "finance.currency.update", "description": "Permission to update currencies and exchange rates", "module_name": "finance"},
    {"name": "Delete Currency", "code": "finance.currency.delete", "description": "Permission to delete currencies and exchange rates", "module_name": "finance"},

    {"name": "Create Cost Center", "code": "finance.costcenter.create", "description": "Permission to create cost centers and dimensions", "module_name": "finance"},
    {"name": "Read Cost Center", "code": "finance.costcenter.read", "description": "Permission to view cost centers and dimensions", "module_name": "finance"},
    {"name": "Update Cost Center", "code": "finance.costcenter.update", "description": "Permission to update cost centers and dimensions", "module_name": "finance"},
    {"name": "Delete Cost Center", "code": "finance.costcenter.delete", "description": "Permission to delete cost centers and dimensions", "module_name": "finance"},

    {"name": "Create Fiscal", "code": "finance.fiscal.create", "description": "Permission to create fiscal years and periods", "module_name": "finance"},
    {"name": "Read Fiscal", "code": "finance.fiscal.read", "description": "Permission to view fiscal years and periods", "module_name": "finance"},
    {"name": "Update Fiscal", "code": "finance.fiscal.update", "description": "Permission to update fiscal years and periods", "module_name": "finance"},
    {"name": "Delete Fiscal", "code": "finance.fiscal.delete", "description": "Permission to delete fiscal years and periods", "module_name": "finance"},
    {"name": "Lock Fiscal Period", "code": "finance.fiscal.lock", "description": "Permission to lock and unlock fiscal periods", "module_name": "finance"},
    {"name": "Close Fiscal Period", "code": "finance.fiscal.close", "description": "Permission to close fiscal periods and years", "module_name": "finance"},

    # Finance Operations & Reporting Permissions
    {"name": "Read Accounts Receivable", "code": "finance.receivable.read", "description": "Permission to view invoices and customer ledgers", "module_name": "finance"},
    {"name": "Create Accounts Receivable", "code": "finance.receivable.create", "description": "Permission to create customer invoices", "module_name": "finance"},
    {"name": "Update Accounts Receivable", "code": "finance.receivable.write", "description": "Permission to modify customer invoices", "module_name": "finance"},
    {"name": "Delete Accounts Receivable", "code": "finance.receivable.delete", "description": "Permission to delete customer invoices", "module_name": "finance"},

    {"name": "Read Accounts Payable", "code": "finance.payable.read", "description": "Permission to view bills and supplier ledgers", "module_name": "finance"},
    {"name": "Create Accounts Payable", "code": "finance.payable.create", "description": "Permission to create supplier bills", "module_name": "finance"},
    {"name": "Update Accounts Payable", "code": "finance.payable.write", "description": "Permission to modify supplier bills", "module_name": "finance"},
    {"name": "Delete Accounts Payable", "code": "finance.payable.delete", "description": "Permission to delete supplier bills", "module_name": "finance"},

    {"name": "Read Payment Vouchers", "code": "finance.payment.read", "description": "Permission to view payment/receipt vouchers", "module_name": "finance"},
    {"name": "Create Payment Vouchers", "code": "finance.payment.create", "description": "Permission to create payment/receipt vouchers", "module_name": "finance"},
    {"name": "Update Payment Vouchers", "code": "finance.payment.write", "description": "Permission to update payment/receipt vouchers", "module_name": "finance"},
    {"name": "Post Payment Vouchers", "code": "finance.payment.post", "description": "Permission to post payment/receipt vouchers", "module_name": "finance"},

    {"name": "Read Bank Management", "code": "finance.bank.read", "description": "Permission to view bank accounts and transactions", "module_name": "finance"},
    {"name": "Create Bank Management", "code": "finance.bank.create", "description": "Permission to create bank accounts", "module_name": "finance"},
    {"name": "Update Bank Management", "code": "finance.bank.write", "description": "Permission to modify bank accounts", "module_name": "finance"},
    {"name": "Delete Bank Management", "code": "finance.bank.delete", "description": "Permission to delete bank accounts", "module_name": "finance"},

    {"name": "Read Reconciliation", "code": "finance.reconciliation.read", "description": "Permission to view bank reconciliations", "module_name": "finance"},
    {"name": "Update Reconciliation", "code": "finance.reconciliation.write", "description": "Permission to modify bank reconciliations", "module_name": "finance"},
    {"name": "Reconcile Bank", "code": "finance.reconciliation.reconcile", "description": "Permission to execute bank reconciliation", "module_name": "finance"},

    {"name": "Read Assets", "code": "finance.asset.read", "description": "Permission to view fixed asset register", "module_name": "finance"},
    {"name": "Create Assets", "code": "finance.asset.create", "description": "Permission to create fixed asset categories/assets", "module_name": "finance"},
    {"name": "Update Assets", "code": "finance.asset.write", "description": "Permission to update fixed assets", "module_name": "finance"},
    {"name": "Dispose Assets", "code": "finance.asset.dispose", "description": "Permission to dispose fixed assets", "module_name": "finance"},

    {"name": "Read Depreciation", "code": "finance.depreciation.read", "description": "Permission to view depreciation schedules", "module_name": "finance"},
    {"name": "Post Depreciation", "code": "finance.depreciation.post", "description": "Permission to post depreciation entries", "module_name": "finance"},

    {"name": "Read Statements", "code": "finance.statement.read", "description": "Permission to view financial statements", "module_name": "finance"},
    {"name": "Generate Statements", "code": "finance.statement.generate", "description": "Permission to generate financial statements", "module_name": "finance"},
    {"name": "Export Statements", "code": "finance.statement.export", "description": "Permission to export financial statements", "module_name": "finance"},

    {"name": "Read Budgets", "code": "finance.budget.read", "description": "Permission to view budgets", "module_name": "finance"},
    {"name": "Create Budgets", "code": "finance.budget.create", "description": "Permission to create budgets", "module_name": "finance"},
    {"name": "Approve Budgets", "code": "finance.budget.approve", "description": "Permission to approve budgets", "module_name": "finance"},
    {"name": "Revise Budgets", "code": "finance.budget.revise", "description": "Permission to revise budgets", "module_name": "finance"},

    {"name": "Read Finance Analytics", "code": "finance.analytics.read", "description": "Permission to view executive finance analytics", "module_name": "finance"},

    # Enterprise Reporting & BI Domain Permissions
    {"name": "Read Centralized Management Dashboard", "code": "reports.dashboard.read", "description": "Permission to view management dashboard", "module_name": "reporting"},
    {"name": "Read Centralized Finance Reports", "code": "reports.finance.read", "description": "Permission to view finance reports", "module_name": "reporting"},
    {"name": "Read Centralized Sales Reports", "code": "reports.sales.read", "description": "Permission to view sales reports", "module_name": "reporting"},
    {"name": "Read Centralized Procurement Reports", "code": "reports.procurement.read", "description": "Permission to view procurement reports", "module_name": "reporting"},
    {"name": "Read Centralized Inventory Reports", "code": "reports.inventory.read", "description": "Permission to view inventory reports", "module_name": "reporting"},
    {"name": "Read Centralized HR Reports", "code": "reports.hr.read", "description": "Permission to view HR reports", "module_name": "reporting"},
    {"name": "Read Centralized Payroll Reports", "code": "reports.payroll.read", "description": "Permission to view payroll reports", "module_name": "reporting"},
    {"name": "Read Centralized CRM Reports", "code": "reports.crm.read", "description": "Permission to view CRM reports", "module_name": "reporting"},
    {"name": "Export Centralized Reports", "code": "reports.export", "description": "Permission to export CSV reports", "module_name": "reporting"},

    {"name": "View Dashboard", "code": "report.dashboard.view", "description": "Permission to view executive and module dashboards", "module_name": "reporting"},
    {"name": "Manage Dashboard", "code": "report.dashboard.manage", "description": "Permission to create and modify dashboards", "module_name": "reporting"},
    {"name": "View Analytics", "code": "report.analytics.view", "description": "Permission to view cross-module analytics and trends", "module_name": "reporting"},
    {"name": "Create Custom Report", "code": "report.builder.create", "description": "Permission to build custom reports", "module_name": "reporting"},
    {"name": "Share Report", "code": "report.builder.share", "description": "Permission to share custom reports", "module_name": "reporting"},
    {"name": "View KPI", "code": "report.kpi.view", "description": "Permission to view system KPIs and metrics", "module_name": "reporting"},
    {"name": "Manage KPI", "code": "report.kpi.manage", "description": "Permission to create and configure KPIs", "module_name": "reporting"},
    {"name": "Export Report", "code": "report.export.execute", "description": "Permission to export reports in PDF/Excel/CSV/JSON", "module_name": "reporting"},
    {"name": "Manage Schedules", "code": "report.schedule.manage", "description": "Permission to manage scheduled report tasks", "module_name": "reporting"},

    # Infrastructure & Production Readiness Permissions
    {"name": "Manage System Platform", "code": "system.manage", "description": "Permission to manage system configurations and health", "module_name": "integrations"},
    {"name": "Read System Metrics", "code": "monitoring.read", "description": "Permission to view observability metrics and health checks", "module_name": "integrations"},
    {"name": "Manage API Keys", "code": "apikey.manage", "description": "Permission to create, rotate, and revoke API keys", "module_name": "integrations"},
    {"name": "Manage Webhooks", "code": "webhook.manage", "description": "Permission to register, view, and replay webhooks", "module_name": "integrations"},
    {"name": "Manage Integrations", "code": "integration.manage", "description": "Permission to configure external storage and communication providers", "module_name": "integrations"},
    {"name": "Manage Backups", "code": "backup.manage", "description": "Permission to trigger and restore database backups", "module_name": "integrations"},
]


DEFAULT_ROLES: List[Dict[str, str]] = [
    {"name": "Super Admin", "description": "Unrestricted administrative authority across all modules"},
    {"name": "HR Manager", "description": "Human Resources management privileges"},
    {"name": "HR Executive", "description": "Human Resources operational privileges"},
    {"name": "Inventory Manager", "description": "Stock and warehouse management privileges"},
    {"name": "Procurement Manager", "description": "Purchasing and supplier management privileges"},
    {"name": "Procurement Viewer", "description": "Read-only access to procurement records"},
    {"name": "Sales Manager", "description": "Sales orders and revenue management privileges"},
    {"name": "Sales Representative", "description": "Operational sales, quotations, and order creation privileges"},
    {"name": "Sales Viewer", "description": "Read-only access to sales records"},
    {"name": "CRM Manager", "description": "Lead acquisition, sales pipeline, and campaign management privileges"},
    {"name": "CRM Viewer", "description": "Read-only access to CRM records"},
    {"name": "Finance Manager", "description": "General Ledger, posting rules, taxes, and fiscal management privileges"},
    {"name": "Chief Accountant", "description": "Accounting journal entry, posting, and period locking privileges"},
    {"name": "Accountant", "description": "Accounting operational privileges for journals and ledger access"},
    {"name": "Finance Viewer", "description": "Read-only access to financial accounts, ledgers, and reports"},
    {"name": "Employee", "description": "Basic employee access privileges"},
]

DEFAULT_TRANSACTION_TYPES: List[Dict[str, str]] = [
    {"code": "OPENING_STOCK", "name": "Opening Stock", "direction": "IN", "description": "Initial stock entry upon product or warehouse initialization"},
    {"code": "PURCHASE_RECEIPT", "name": "Purchase Receipt", "direction": "IN", "description": "Stock received from procurement vendor"},
    {"code": "SALES_ISSUE", "name": "Sales Issue", "direction": "OUT", "description": "Stock issued for sales fulfillment"},
    {"code": "STOCK_ADJUSTMENT", "name": "Stock Adjustment", "direction": "ADJUSTMENT", "description": "Physical count adjustment or variance correction"},
    {"code": "TRANSFER_IN", "name": "Transfer In", "direction": "IN", "description": "Internal stock transfer received"},
    {"code": "TRANSFER_OUT", "name": "Transfer Out", "direction": "OUT", "description": "Internal stock transfer issued"},
    {"code": "PRODUCTION_RECEIPT", "name": "Production Receipt", "direction": "IN", "description": "Finished goods received from manufacturing"},
    {"code": "PRODUCTION_CONSUMPTION", "name": "Production Consumption", "direction": "OUT", "description": "Raw materials consumed in manufacturing"},
    {"code": "RETURN_IN", "name": "Return In", "direction": "IN", "description": "Customer sales return received"},
    {"code": "RETURN_OUT", "name": "Return Out", "direction": "OUT", "description": "Vendor purchase return issued"},
    {"code": "CYCLE_COUNT", "name": "Cycle Count", "direction": "ADJUSTMENT", "description": "Cycle count audit variance"},
    {"code": "SYSTEM_CORRECTION", "name": "System Correction", "direction": "SYSTEM", "description": "Automated system balance reconciliation"},
]


async def seed_rbac_data(db: AsyncSession) -> None:
    """
    Idempotently seeds default roles, permission definitions, and inventory transaction types into database.
    """
    logger.info("Seeding RBAC permissions, default roles, and inventory transaction types...")
    
    # 1. Seed Permissions
    created_perms = {}
    for p_data in DEFAULT_PERMISSIONS:
        existing = await permission_repository.get_by_code(db, p_data["code"])
        if not existing:
            perm_in = PermissionCreate(**p_data)
            existing = await permission_repository.create_permission(db, obj_in=perm_in)
            logger.info(f"Seeded permission: {p_data['code']}")
        created_perms[p_data["code"]] = existing

    # 2. Seed Roles
    created_roles = {}
    for r_data in DEFAULT_ROLES:
        existing = await role_repository.get_by_name(db, r_data["name"])
        if not existing:
            role_in = RoleCreate(**r_data)
            existing = await role_repository.create_role(db, obj_in=role_in)
            logger.info(f"Seeded role: {r_data['name']}")
        created_roles[r_data["name"]] = existing

    # 3. Seed Inventory Transaction Types
    from app.repositories.stock_engine_repos import inventory_transaction_type_repository
    for t_data in DEFAULT_TRANSACTION_TYPES:
        existing = await inventory_transaction_type_repository.get_by_code(db, t_data["code"])
        if not existing:
            await inventory_transaction_type_repository.create(db, obj_in=t_data)
            logger.info(f"Seeded inventory transaction type: {t_data['code']}")

    # 4. Assign Permissions to Roles
    super_admin_role = created_roles.get("Super Admin")
    hr_manager_role = created_roles.get("HR Manager")
    inventory_manager_role = created_roles.get("Inventory Manager")
    procurement_manager_role = created_roles.get("Procurement Manager")
    procurement_viewer_role = created_roles.get("Procurement Viewer")
    sales_manager_role = created_roles.get("Sales Manager")
    sales_rep_role = created_roles.get("Sales Representative")
    sales_viewer_role = created_roles.get("Sales Viewer")
    crm_manager_role = created_roles.get("CRM Manager")
    crm_viewer_role = created_roles.get("CRM Viewer")
    finance_manager_role = created_roles.get("Finance Manager")
    chief_accountant_role = created_roles.get("Chief Accountant")
    accountant_role = created_roles.get("Accountant")
    finance_viewer_role = created_roles.get("Finance Viewer")

    for perm_code, perm_obj in created_perms.items():
        if super_admin_role:
            await role_permission_repository.assign_permission_to_role(
                db, role_id=super_admin_role.id, permission_id=perm_obj.id
            )
        if hr_manager_role and (
            perm_code.startswith("department.")
            or perm_code.startswith("employee.")
            or perm_code.startswith("employee_document.")
            or perm_code.startswith("position.")
            or perm_code.startswith("hr_configuration.")
            or perm_code.startswith("shift.")
            or perm_code.startswith("holiday.")
            or perm_code.startswith("attendance.")
        ):
            await role_permission_repository.assign_permission_to_role(
                db, role_id=hr_manager_role.id, permission_id=perm_obj.id
            )
        if inventory_manager_role and perm_code.startswith("inventory."):
            await role_permission_repository.assign_permission_to_role(
                db, role_id=inventory_manager_role.id, permission_id=perm_obj.id
            )
        if procurement_manager_role and perm_code.startswith("procurement."):
            await role_permission_repository.assign_permission_to_role(
                db, role_id=procurement_manager_role.id, permission_id=perm_obj.id
            )
        if procurement_viewer_role and (
            perm_code.startswith("procurement.") and (perm_code.endswith(".read") or perm_code.endswith(".compare"))
        ):
            await role_permission_repository.assign_permission_to_role(
                db, role_id=procurement_viewer_role.id, permission_id=perm_obj.id
            )
        if sales_manager_role and perm_code.startswith("sales."):
            await role_permission_repository.assign_permission_to_role(
                db, role_id=sales_manager_role.id, permission_id=perm_obj.id
            )
        if sales_rep_role and (
            perm_code in [
                "sales.customer.create", "sales.customer.read", "sales.customer.update",
                "sales.quotation.create", "sales.quotation.read", "sales.quotation.update", "sales.quotation.submit", "sales.quotation.cancel",
                "sales.order.create", "sales.order.read", "sales.order.update", "sales.order.submit", "sales.order.cancel",
                "sales.delivery.create", "sales.delivery.read", "sales.delivery.update",
                "sales.return.create", "sales.return.read",
                "sales.pricing.read",
                "crm.lead.create", "crm.lead.read", "crm.lead.update", "crm.lead.convert",
                "crm.opportunity.create", "crm.opportunity.read", "crm.opportunity.update", "crm.opportunity.stage",
                "crm.activity.create", "crm.activity.read", "crm.activity.update", "crm.activity.delete",
                "crm.meeting.create", "crm.meeting.read", "crm.meeting.update",
                "crm.task.create", "crm.task.read", "crm.task.update",
                "crm.search.read",
            ]
        ):
            await role_permission_repository.assign_permission_to_role(
                db, role_id=sales_rep_role.id, permission_id=perm_obj.id
            )
        if sales_viewer_role and (
            (perm_code.startswith("sales.") and perm_code.endswith(".read"))
            or (perm_code.startswith("crm.") and (perm_code.endswith(".read") or perm_code.endswith(".search")))
        ):
            await role_permission_repository.assign_permission_to_role(
                db, role_id=sales_viewer_role.id, permission_id=perm_obj.id
            )
        if crm_manager_role and (perm_code.startswith("crm.") or perm_code == "sales.customer.read"):
            await role_permission_repository.assign_permission_to_role(
                db, role_id=crm_manager_role.id, permission_id=perm_obj.id
            )
        if crm_viewer_role and (
            (perm_code.startswith("crm.") and (perm_code.endswith(".read") or perm_code.endswith(".search")))
            or perm_code == "sales.customer.read"
        ):
            await role_permission_repository.assign_permission_to_role(
                db, role_id=crm_viewer_role.id, permission_id=perm_obj.id
            )
        if (finance_manager_role or chief_accountant_role) and perm_code.startswith("finance."):
            if finance_manager_role:
                await role_permission_repository.assign_permission_to_role(
                    db, role_id=finance_manager_role.id, permission_id=perm_obj.id
                )
            if chief_accountant_role:
                await role_permission_repository.assign_permission_to_role(
                    db, role_id=chief_accountant_role.id, permission_id=perm_obj.id
                )
        if accountant_role and (
            perm_code in [
                "finance.company.read",
                "finance.accounts.read",
                "finance.journal.create",
                "finance.journal.read",
                "finance.journal.update",
                "finance.journal.post",
                "finance.journal.reverse",
                "finance.journal.cancel",
                "finance.ledger.read",
                "finance.reports.read",
                "finance.fiscal.read",
                "finance.currency.read",
                "finance.tax.read",
                "finance.costcenter.read",
                "finance.receivable.read",
                "finance.receivable.create",
                "finance.payable.read",
                "finance.payable.create",
                "finance.payment.read",
                "finance.payment.create",
                "finance.payment.post",
            ]
        ):
            await role_permission_repository.assign_permission_to_role(
                db, role_id=accountant_role.id, permission_id=perm_obj.id
            )
        if finance_viewer_role and (
            perm_code.startswith("finance.") and (
                perm_code.endswith(".read")
                or perm_code.endswith(".view")
            )
        ):
            await role_permission_repository.assign_permission_to_role(
                db, role_id=finance_viewer_role.id, permission_id=perm_obj.id
            )

    # 5. Seed Default Super Admin User if not exists
    from app.repositories.user import user_repository
    from app.core.security import hash_password
    from app.models.user_role import UserRole
    from sqlalchemy import select

    admin_email = "admin@apnaerp.com"
    existing_admin = await user_repository.get_by_email(db, admin_email)
    if not existing_admin:
        admin_user = User(
            full_name="ERP Admin",
            email=admin_email,
            username="admin",
            password_hash=hash_password("admin123"),
            is_active=True,
            is_superuser=True,
        )
        db.add(admin_user)
        await db.flush()
        if super_admin_role:
            stmt = select(UserRole).where(UserRole.user_id == admin_user.id, UserRole.role_id == super_admin_role.id)
            has_role = (await db.execute(stmt)).scalars().first()
            if not has_role:
                db.add(UserRole(user_id=admin_user.id, role_id=super_admin_role.id))
        await db.commit()
        logger.info(f"Seeded default Super Admin user: {admin_email}")



async def run_seed() -> None:
    """
    Standalone runner for database seeding.
    """
    async with AsyncSessionLocal() as session:
        await seed_rbac_data(session)


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_seed())



