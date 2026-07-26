import uuid
from typing import List, Set
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.permission import Permission
from app.models.role import Role
from app.repositories.rbac import (
    permission_repository,
    role_permission_repository,
    role_repository,
    user_role_repository,
)
from app.repositories.user import user_repository
from app.schemas.rbac import PermissionCreate, RoleCreate, RoleUpdate
from app.services.base import BaseService


class RBACService(BaseService[role_repository.__class__]):
    """
    Service layer handling Role-Based Access Control business logic.
    """
    def __init__(self):
        super().__init__(role_repository)

    async def get_roles(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Role]:
        return await self.repository.get_all(db, skip=skip, limit=limit)

    async def get_role_by_id(self, db: AsyncSession, role_id: uuid.UUID) -> Role:
        role = await self.repository.get_by_id(db, role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role with ID '{role_id}' not found.",
            )
        return role

    async def create_role(self, db: AsyncSession, role_in: RoleCreate) -> Role:
        existing = await self.repository.get_by_name(db, role_in.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{role_in.name}' already exists.",
            )
        
        role = await self.repository.create_role(db, obj_in=role_in)
        
        # Attach initial permissions if provided
        if role_in.permission_ids:
            for perm_id in role_in.permission_ids:
                perm = await permission_repository.get_by_id(db, perm_id)
                if perm:
                    await role_permission_repository.assign_permission_to_role(
                        db, role_id=role.id, permission_id=perm.id
                    )
            # Re-fetch role with populated permissions
            role = await self.get_role_by_id(db, role.id)
            
        return role

    async def update_role(self, db: AsyncSession, role_id: uuid.UUID, role_in: RoleUpdate) -> Role:
        role = await self.get_role_by_id(db, role_id)
        if role_in.name and role_in.name.lower() != role.name.lower():
            existing = await self.repository.get_by_name(db, role_in.name)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Role name '{role_in.name}' is already taken.",
                )
        return await self.repository.update_role(db, db_obj=role, obj_in=role_in)

    async def delete_role(self, db: AsyncSession, role_id: uuid.UUID) -> None:
        role = await self.get_role_by_id(db, role_id)
        if role.name.lower() == "super admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The 'Super Admin' role cannot be deleted.",
            )
        await self.repository.delete_role(db, id=role_id)

    async def get_permissions(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Permission]:
        return await permission_repository.get_all(db, skip=skip, limit=limit)

    async def create_permission(self, db: AsyncSession, perm_in: PermissionCreate) -> Permission:
        existing_code = await permission_repository.get_by_code(db, perm_in.code)
        if existing_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Permission code '{perm_in.code}' already exists.",
            )
        existing_name = await permission_repository.get_by_name(db, perm_in.name)
        if existing_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Permission name '{perm_in.name}' already exists.",
            )
        return await permission_repository.create_permission(db, obj_in=perm_in)

    async def assign_role_to_user(self, db: AsyncSession, user_id: uuid.UUID, role_id: uuid.UUID) -> None:
        user = await user_repository.get_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID '{user_id}' not found.",
            )
        role = await self.get_role_by_id(db, role_id)
        assigned = await user_role_repository.assign_role_to_user(db, user_id=user_id, role_id=role_id)
        if not assigned:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{role.name}' is already assigned to user.",
            )

    async def remove_role_from_user(self, db: AsyncSession, user_id: uuid.UUID, role_id: uuid.UUID) -> None:
        user = await user_repository.get_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID '{user_id}' not found.",
            )
        removed = await user_role_repository.remove_role_from_user(db, user_id=user_id, role_id=role_id)
        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User role assignment not found.",
            )

    async def assign_permission_to_role(self, db: AsyncSession, role_id: uuid.UUID, permission_id: uuid.UUID) -> Role:
        role = await self.get_role_by_id(db, role_id)
        perm = await permission_repository.get_by_id(db, permission_id)
        if not perm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Permission with ID '{permission_id}' not found.",
            )
        assigned = await role_permission_repository.assign_permission_to_role(
            db, role_id=role_id, permission_id=permission_id
        )
        if not assigned:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Permission '{perm.code}' is already assigned to role '{role.name}'.",
            )
        return await self.get_role_by_id(db, role_id)

    async def remove_permission_from_role(self, db: AsyncSession, role_id: uuid.UUID, permission_id: uuid.UUID) -> Role:
        role = await self.get_role_by_id(db, role_id)
        removed = await role_permission_repository.remove_permission_from_role(
            db, role_id=role_id, permission_id=permission_id
        )
        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role permission assignment not found.",
            )
        return await self.get_role_by_id(db, role_id)

    async def get_user_permission_codes(self, db: AsyncSession, user_id: uuid.UUID) -> Set[str]:
        """
        Collects all distinct permission codes granted to the user through all assigned roles.
        """
        roles = await user_role_repository.get_user_roles(db, user_id=user_id)
        permission_codes: Set[str] = set()
        for role in roles:
            for perm in role.permissions:
                permission_codes.add(perm.code)
        return permission_codes


rbac_service = RBACService()
