from typing import List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.repositories.base_repository import BaseRepository
from app.schemas.employee import EmployeeCreate, EmployeeUpdate


class EmployeeRepository(BaseRepository[Employee, EmployeeCreate, EmployeeUpdate]):
    """
    Repository handling database access for Employee ORM model.
    Provides methods for employee code, work email, department lookup, manager reporting queries, and existence checks.
    """
    def __init__(self):
        super().__init__(Employee)

    async def get_by_code(self, db: AsyncSession, code: str, include_deleted: bool = False) -> Optional[Employee]:
        """Fetches employee by unique employee code."""
        stmt = select(Employee).where(Employee.employee_code == code)
        if not include_deleted:
            stmt = stmt.where(Employee.is_deleted == False)
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_by_work_email(self, db: AsyncSession, email: str, include_deleted: bool = False) -> Optional[Employee]:
        """Fetches employee by unique work email address."""
        stmt = select(Employee).where(Employee.work_email == email)
        if not include_deleted:
            stmt = stmt.where(Employee.is_deleted == False)
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_by_user_id(self, db: AsyncSession, user_id: uuid.UUID, include_deleted: bool = False) -> Optional[Employee]:
        """Fetches employee by linked User ID."""
        stmt = select(Employee).where(Employee.user_id == user_id)
        if not include_deleted:
            stmt = stmt.where(Employee.is_deleted == False)
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_by_department(self, db: AsyncSession, department_id: uuid.UUID) -> List[Employee]:
        """Fetches active non-deleted employees assigned to a specific department."""
        stmt = (
            select(Employee)
            .where(Employee.department_id == department_id, Employee.is_deleted == False)
            .order_by(Employee.first_name, Employee.last_name)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def get_direct_reports(self, db: AsyncSession, manager_id: uuid.UUID) -> List[Employee]:
        """Fetches active non-deleted direct report employees reporting to manager_id."""
        stmt = (
            select(Employee)
            .where(Employee.manager_id == manager_id, Employee.is_deleted == False)
            .order_by(Employee.first_name, Employee.last_name)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def exists_by_code(self, db: AsyncSession, code: str, exclude_id: Optional[uuid.UUID] = None) -> bool:
        """Checks if employee code exists."""
        stmt = select(Employee).where(Employee.employee_code == code, Employee.is_deleted == False)
        if exclude_id:
            stmt = stmt.where(Employee.id != exclude_id)
        res = await db.execute(stmt)
        return res.scalars().first() is not None

    async def exists_by_work_email(self, db: AsyncSession, email: str, exclude_id: Optional[uuid.UUID] = None) -> bool:
        """Checks if work email exists."""
        stmt = select(Employee).where(Employee.work_email == email, Employee.is_deleted == False)
        if exclude_id:
            stmt = stmt.where(Employee.id != exclude_id)
        res = await db.execute(stmt)
        return res.scalars().first() is not None

    async def exists_by_user_id(self, db: AsyncSession, user_id: uuid.UUID, exclude_id: Optional[uuid.UUID] = None) -> bool:
        """Checks if user ID is already linked to an employee."""
        stmt = select(Employee).where(Employee.user_id == user_id, Employee.is_deleted == False)
        if exclude_id:
            stmt = stmt.where(Employee.id != exclude_id)
        res = await db.execute(stmt)
        return res.scalars().first() is not None


employee_repository = EmployeeRepository()
