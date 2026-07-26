import uuid
from typing import Any, List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, has_permission, has_role
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.rbac import (
    PermissionCreate,
    PermissionResponse,
    RoleCreate,
    RolePermissionAssign,
    RoleResponse,
    RoleUpdate,
    UserRoleAssign,
)
from app.services.rbac import rbac_service

router = APIRouter()


# --- ROLES ENDPOINTS ---

@router.get(
    "/roles",
    response_model=List[RoleResponse],
    status_code=status.HTTP_200_OK,
    summary="List Roles",
    description="Lists all security roles and their assigned permissions.",
)
async def get_roles(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    return await rbac_service.get_roles(db, skip=skip, limit=limit)


@router.post(
    "/roles",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Role",
    description="Creates a new security role. Requires 'roles.create' permission or Super Admin.",
)
async def create_role(
    role_in: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("roles.create")),
) -> Any:
    return await rbac_service.create_role(db, role_in=role_in)


@router.put(
    "/roles/{id}",
    response_model=RoleResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Role",
    description="Updates a role's title or description. Requires 'roles.update' permission or Super Admin.",
)
async def update_role(
    id: uuid.UUID,
    role_in: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("roles.update")),
) -> Any:
    return await rbac_service.update_role(db, role_id=id, role_in=role_in)


@router.delete(
    "/roles/{id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete Role",
    description="Deletes a security role. Requires 'roles.delete' permission or Super Admin.",
)
async def delete_role(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("roles.delete")),
) -> Any:
    await rbac_service.delete_role(db, role_id=id)
    return MessageResponse(message=f"Role '{id}' deleted successfully.")


# --- PERMISSIONS ENDPOINTS ---

@router.get(
    "/permissions",
    response_model=List[PermissionResponse],
    status_code=status.HTTP_200_OK,
    summary="List Permissions",
    description="Lists all permission definitions registered in the ERP system.",
)
async def get_permissions(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    return await rbac_service.get_permissions(db, skip=skip, limit=limit)


@router.post(
    "/permissions",
    response_model=PermissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Permission",
    description="Registers a new system permission code. Requires 'admin.full_access' or Super Admin.",
)
async def create_permission(
    perm_in: PermissionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("admin.full_access")),
) -> Any:
    return await rbac_service.create_permission(db, perm_in=perm_in)


# --- USER ROLE ASSIGNMENTS ---

@router.post(
    "/users/{user_id}/roles",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Assign Role to User",
    description="Assigns a security role to a user. Requires 'roles.update' permission or Super Admin.",
)
async def assign_role_to_user(
    user_id: uuid.UUID,
    assignment: UserRoleAssign,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("roles.update")),
) -> Any:
    await rbac_service.assign_role_to_user(db, user_id=user_id, role_id=assignment.role_id)
    return MessageResponse(message=f"Role '{assignment.role_id}' assigned to user '{user_id}'.")


@router.delete(
    "/users/{user_id}/roles/{role_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove Role from User",
    description="Removes a security role assignment from a user. Requires 'roles.update' permission or Super Admin.",
)
async def remove_role_from_user(
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("roles.update")),
) -> Any:
    await rbac_service.remove_role_from_user(db, user_id=user_id, role_id=role_id)
    return MessageResponse(message=f"Role '{role_id}' removed from user '{user_id}'.")


# --- ROLE PERMISSION ASSIGNMENTS ---

@router.post(
    "/roles/{role_id}/permissions",
    response_model=RoleResponse,
    status_code=status.HTTP_200_OK,
    summary="Assign Permission to Role",
    description="Grants a permission code to a role. Requires 'roles.update' permission or Super Admin.",
)
async def assign_permission_to_role(
    role_id: uuid.UUID,
    assignment: RolePermissionAssign,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("roles.update")),
) -> Any:
    return await rbac_service.assign_permission_to_role(
        db, role_id=role_id, permission_id=assignment.permission_id
    )


@router.delete(
    "/roles/{role_id}/permissions/{permission_id}",
    response_model=RoleResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove Permission from Role",
    description="Revokes a permission code from a role. Requires 'roles.update' permission or Super Admin.",
)
async def remove_permission_from_role(
    role_id: uuid.UUID,
    permission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("roles.update")),
) -> Any:
    return await rbac_service.remove_permission_from_role(
        db, role_id=role_id, permission_id=permission_id
    )
