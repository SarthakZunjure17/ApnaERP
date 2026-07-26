from typing import List, Optional
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.models.shift import Shift
from app.repositories.base_repository import BaseRepository
from app.schemas.shift import ShiftCreate, ShiftUpdate


class ShiftRepository(BaseRepository[Shift, ShiftCreate, ShiftUpdate]):
    """
    Repository layer for Shift entity.
    Provides database access methods for shift schedules, code/name lookups, and assigned employee counts.
    """
    def __init__(self):
        super().__init__(Shift)

    async def get_by_code(
        self, db: AsyncSession, code: str, include_deleted: bool = False
    ) -> Optional[Shift]:
        """Retrieves a Shift by unique code."""
        query = select(Shift).where(func.lower(Shift.code) == code.lower())
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)
        res = await db.execute(query)
        return res.scalars().first()

    async def get_by_name(
        self, db: AsyncSession, name: str, include_deleted: bool = False
    ) -> Optional[Shift]:
        """Retrieves a Shift by unique name."""
        query = select(Shift).where(func.lower(Shift.name) == name.lower())
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)
        res = await db.execute(query)
        return res.scalars().first()

    async def exists_by_code(
        self, db: AsyncSession, code: str, include_deleted: bool = False
    ) -> bool:
        """Checks if a shift code exists."""
        query = select(func.count()).select_from(Shift).where(func.lower(Shift.code) == code.lower())
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)
        res = await db.execute(query)
        count = res.scalar_one_or_none() or 0
        return count > 0

    async def exists_by_name(
        self, db: AsyncSession, name: str, include_deleted: bool = False
    ) -> bool:
        """Checks if a shift name exists."""
        query = select(func.count()).select_from(Shift).where(func.lower(Shift.name) == name.lower())
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)
        res = await db.execute(query)
        count = res.scalar_one_or_none() or 0
        return count > 0

    async def get_assigned_employee_count(
        self, db: AsyncSession, shift_id: uuid.UUID
    ) -> int:
        """Retrieves count of active employees assigned to a shift schedule."""
        query = select(func.count()).select_from(Employee).where(
            Employee.shift_id == shift_id,
            Employee.is_deleted.is_(False),
        )
        res = await db.execute(query)
        return res.scalar_one_or_none() or 0


shift_repository = ShiftRepository()
