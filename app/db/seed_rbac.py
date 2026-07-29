import logging
from typing import Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal
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

    {"name": "Create Product Attribute", "code": "inventory.attribute.create", "description": "Permission to create product attributes", "module_name": "inventory"},
    {"name": "Read Product Attribute", "code": "inventory.attribute.read", "description": "Permission to view product attributes", "module_name": "inventory"},
    {"name": "Update Product Attribute", "code": "inventory.attribute.update", "description": "Permission to update product attributes", "module_name": "inventory"},
    {"name": "Delete Product Attribute", "code": "inventory.attribute.delete", "description": "Permission to delete product attributes", "module_name": "inventory"},

    {"name": "Upload Product Document", "code": "inventory.document.upload", "description": "Permission to upload product documents", "module_name": "inventory"},
    {"name": "Read Product Document", "code": "inventory.document.read", "description": "Permission to view product documents", "module_name": "inventory"},
    {"name": "Delete Product Document", "code": "inventory.document.delete", "description": "Permission to delete product documents", "module_name": "inventory"},

    # Inventory
    {"name": "Create Inventory Items", "code": "inventory.create", "description": "Permission to add inventory stock", "module_name": "inventory"},
    {"name": "Read Inventory Items", "code": "inventory.read", "description": "Permission to view inventory stock", "module_name": "inventory"},
    {"name": "Update Inventory Items", "code": "inventory.update", "description": "Permission to modify inventory stock", "module_name": "inventory"},
    {"name": "Delete Inventory Items", "code": "inventory.delete", "description": "Permission to delete inventory stock", "module_name": "inventory"},
]

DEFAULT_ROLES: List[Dict[str, str]] = [
    {"name": "Super Admin", "description": "Unrestricted administrative authority across all modules"},
    {"name": "HR Manager", "description": "Human Resources management privileges"},
    {"name": "HR Executive", "description": "Human Resources operational privileges"},
    {"name": "Inventory Manager", "description": "Stock and warehouse management privileges"},
    {"name": "Sales Manager", "description": "Sales orders and revenue management privileges"},
    {"name": "Employee", "description": "Basic employee access privileges"},
]


async def seed_rbac_data(db: AsyncSession) -> None:
    """
    Idempotently seeds default roles and permission definitions into database.
    """
    logger.info("Seeding RBAC permissions and default roles...")
    
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

    # 3. Assign Permissions to Super Admin & HR Manager & Inventory Manager
    super_admin_role = created_roles.get("Super Admin")
    hr_manager_role = created_roles.get("HR Manager")
    inventory_manager_role = created_roles.get("Inventory Manager")

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


async def run_seed() -> None:
    """
    Standalone runner for database seeding.
    """
    async with AsyncSessionLocal() as session:
        await seed_rbac_data(session)
