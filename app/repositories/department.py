from typing import List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.department import Department
from app.repositories.base_repository import BaseRepository
from app.schemas.department import DepartmentCreate, DepartmentUpdate


class DepartmentRepository(BaseRepository[Department, DepartmentCreate, DepartmentUpdate]):
    """
    Repository handling database operations for Department model.
    Inherits generic CRUD functionality and adds hierarchy/tree retrieval methods.
    """
    def __init__(self):
        super().__init__(Department)

    async def get_by_code(self, db: AsyncSession, code: str, include_deleted: bool = False) -> Optional[Department]:
        """Fetches a department by its unique code."""
        stmt = select(Department).where(Department.code == code)
        if not include_deleted:
            stmt = stmt.where(Department.is_deleted == False)
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_by_name(self, db: AsyncSession, name: str, include_deleted: bool = False) -> Optional[Department]:
        """Fetches a department by its unique name."""
        stmt = select(Department).where(Department.name == name)
        if not include_deleted:
            stmt = stmt.where(Department.is_deleted == False)
        res = await db.execute(stmt)
        return res.scalars().first()

    async def exists_by_code(self, db: AsyncSession, code: str, exclude_id: Optional[uuid.UUID] = None) -> bool:
        """Checks if a department code already exists, excluding an optional ID."""
        stmt = select(Department).where(Department.code == code, Department.is_deleted == False)
        if exclude_id:
            stmt = stmt.where(Department.id != exclude_id)
        res = await db.execute(stmt)
        return res.scalars().first() is not None

    async def exists_by_name(self, db: AsyncSession, name: str, exclude_id: Optional[uuid.UUID] = None) -> bool:
        """Checks if a department name already exists, excluding an optional ID."""
        stmt = select(Department).where(Department.name == name, Department.is_deleted == False)
        if exclude_id:
            stmt = stmt.where(Department.id != exclude_id)
        res = await db.execute(stmt)
        return res.scalars().first() is not None

    async def get_children(self, db: AsyncSession, parent_id: uuid.UUID) -> List[Department]:
        """Retrieves active immediate child departments for a parent ID."""
        stmt = (
            select(Department)
            .where(Department.parent_id == parent_id, Department.is_deleted == False)
            .order_by(Department.name)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def get_tree(self, db: AsyncSession) -> List[Department]:
        """
        Retrieves top-level root departments (parent_id IS NULL) with nested children eagerly loaded.
        """
        stmt = (
            select(Department)
            .where(Department.parent_id == None, Department.is_deleted == False)  # noqa: E711
            .options(selectinload(Department.children))
            .order_by(Department.name)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())


department_repository = DepartmentRepository()
