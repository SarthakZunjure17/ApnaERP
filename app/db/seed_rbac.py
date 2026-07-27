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

    # Inventory
    {"name": "Create Inventory Items", "code": "inventory.create", "description": "Permission to add inventory stock", "module_name": "inventory"},
    {"name": "Read Inventory Items", "code": "inventory.read", "description": "Permission to view inventory stock", "module_name": "inventory"},
    {"name": "Update Inventory Items", "code": "inventory.update", "description": "Permission to modify inventory stock", "module_name": "inventory"},
    {"name": "Delete Inventory Items", "code": "inventory.delete", "description": "Permission to delete inventory stock", "module_name": "inventory"},

    # Sales
    {"name": "Create Sales Orders", "code": "sales.create", "description": "Permission to record sales orders", "module_name": "sales"},
    {"name": "Read Sales Orders", "code": "sales.read", "description": "Permission to view sales orders", "module_name": "sales"},
    {"name": "Update Sales Orders", "code": "sales.update", "description": "Permission to update sales orders", "module_name": "sales"},
    {"name": "Delete Sales Orders", "code": "sales.delete", "description": "Permission to cancel/delete sales orders", "module_name": "sales"},
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

    # 3. Assign Permissions to Super Admin & HR Manager
    super_admin_role = created_roles.get("Super Admin")
    hr_manager_role = created_roles.get("HR Manager")

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


async def run_seed() -> None:
    """
    Standalone runner for database seeding.
    """
    async with AsyncSessionLocal() as session:
        await seed_rbac_data(session)
