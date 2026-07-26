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
        if hr_manager_role and (perm_code.startswith("department.") or perm_code.startswith("employee.") or perm_code.startswith("employee_document.")):
            await role_permission_repository.assign_permission_to_role(
                db, role_id=hr_manager_role.id, permission_id=perm_obj.id
            )


async def run_seed() -> None:
    """
    Standalone runner for database seeding.
    """
    async with AsyncSessionLocal() as session:
        await seed_rbac_data(session)
