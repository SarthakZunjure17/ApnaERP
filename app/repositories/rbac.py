import uuid
from typing import List, Optional
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.permission import Permission
from app.models.role import Role, RolePermission
from app.models.user_role import UserRole
from app.repositories.base import BaseRepository
from app.schemas.rbac import PermissionCreate, PermissionUpdate, RoleCreate, RoleUpdate


class RoleRepository(BaseRepository[Role, RoleCreate, RoleUpdate]):
    """
    Repository for Role entity.
    """
    def __init__(self):
        super().__init__(Role)

    async def get_by_id(self, db: AsyncSession, id: uuid.UUID) -> Optional[Role]:
        result = await db.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.id == id)
            .execution_options(populate_existing=True)
        )
        return result.scalars().first()

    async def get_by_name(self, db: AsyncSession, name: str) -> Optional[Role]:
        result = await db.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(func.lower(Role.name) == name.lower())
            .execution_options(populate_existing=True)
        )
        return result.scalars().first()

    async def get_all(self, db: AsyncSession, *, skip: int = 0, limit: int = 100) -> List[Role]:
        result = await db.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .offset(skip)
            .limit(limit)
            .execution_options(populate_existing=True)
        )
        return list(result.scalars().all())

    async def create_role(self, db: AsyncSession, *, obj_in: RoleCreate) -> Role:
        role = Role(name=obj_in.name, description=obj_in.description)
        db.add(role)
        await db.commit()
        await db.refresh(role)
        return role

    async def update_role(self, db: AsyncSession, *, db_obj: Role, obj_in: RoleUpdate) -> Role:
        if obj_in.name is not None:
            db_obj.name = obj_in.name
        if obj_in.description is not None:
            db_obj.description = obj_in.description
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete_role(self, db: AsyncSession, *, id: uuid.UUID) -> bool:
        role = await self.get_by_id(db, id)
        if role:
            await db.delete(role)
            await db.commit()
            return True
        return False


class PermissionRepository(BaseRepository[Permission, PermissionCreate, PermissionUpdate]):
    """
    Repository for Permission entity.
    """
    def __init__(self):
        super().__init__(Permission)

    async def get_by_id(self, db: AsyncSession, id: uuid.UUID) -> Optional[Permission]:
        result = await db.execute(select(Permission).where(Permission.id == id))
        return result.scalars().first()

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[Permission]:
        result = await db.execute(select(Permission).where(func.lower(Permission.code) == code.lower()))
        return result.scalars().first()

    async def get_by_name(self, db: AsyncSession, name: str) -> Optional[Permission]:
        result = await db.execute(select(Permission).where(func.lower(Permission.name) == name.lower()))
        return result.scalars().first()

    async def get_all(self, db: AsyncSession, *, skip: int = 0, limit: int = 100) -> List[Permission]:
        result = await db.execute(select(Permission).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create_permission(self, db: AsyncSession, *, obj_in: PermissionCreate) -> Permission:
        permission = Permission(
            name=obj_in.name,
            code=obj_in.code,
            description=obj_in.description,
            module_name=obj_in.module_name,
        )
        db.add(permission)
        await db.commit()
        await db.refresh(permission)
        return permission


class UserRoleRepository:
    """
    Repository for UserRole association.
    """
    async def assign_role_to_user(self, db: AsyncSession, *, user_id: uuid.UUID, role_id: uuid.UUID) -> bool:
        result = await db.execute(
            select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
        )
        if result.scalars().first():
            return False  # Already assigned
        
        user_role = UserRole(user_id=user_id, role_id=role_id)
        db.add(user_role)
        await db.commit()
        return True

    async def remove_role_from_user(self, db: AsyncSession, *, user_id: uuid.UUID, role_id: uuid.UUID) -> bool:
        result = await db.execute(
            delete(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
        )
        await db.commit()
        return result.rowcount > 0

    async def get_user_roles(self, db: AsyncSession, *, user_id: uuid.UUID) -> List[Role]:
        result = await db.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        return list(result.scalars().all())


class RolePermissionRepository:
    """
    Repository for RolePermission association.
    """
    async def assign_permission_to_role(self, db: AsyncSession, *, role_id: uuid.UUID, permission_id: uuid.UUID) -> bool:
        result = await db.execute(
            select(RolePermission).where(RolePermission.role_id == role_id, RolePermission.permission_id == permission_id)
        )
        if result.scalars().first():
            return False  # Already assigned
        
        rp = RolePermission(role_id=role_id, permission_id=permission_id)
        db.add(rp)
        await db.commit()
        return True

    async def remove_permission_from_role(self, db: AsyncSession, *, role_id: uuid.UUID, permission_id: uuid.UUID) -> bool:
        result = await db.execute(
            delete(RolePermission).where(RolePermission.role_id == role_id, RolePermission.permission_id == permission_id)
        )
        await db.commit()
        return result.rowcount > 0


role_repository = RoleRepository()
permission_repository = PermissionRepository()
user_role_repository = UserRoleRepository()
role_permission_repository = RolePermissionRepository()
