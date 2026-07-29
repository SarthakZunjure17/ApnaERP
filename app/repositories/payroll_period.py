import datetime
import logging
from typing import Any, List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.employee import Employee
from app.models.payroll_period import PayrollPeriod, PayrollRecord, PayrollRecordComponent
from app.repositories.base_repository import BaseRepository
from app.schemas.payroll_period import (
    PayrollPeriodCreate,
    PayrollPeriodResponse,
)

logger = logging.getLogger("app.repositories.payroll_period")


class PayrollPeriodRepository(
    BaseRepository[PayrollPeriod, PayrollPeriodCreate, PayrollPeriodResponse]
):
    """
    Repository layer for PayrollPeriod entities.
    """

    def __init__(self):
        super().__init__(PayrollPeriod)

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[PayrollPeriod]:
        """Retrieves a PayrollPeriod by its unique period code."""
        query = select(PayrollPeriod).where(PayrollPeriod.period_code == code)
        res = await db.execute(query)
        return res.unique().scalars().first()

    async def get_by_date_range(
        self, db: AsyncSession, start_date: datetime.date, end_date: datetime.date
    ) -> Optional[PayrollPeriod]:
        """Retrieves a PayrollPeriod by start_date and end_date."""
        query = select(PayrollPeriod).where(
            PayrollPeriod.start_date == start_date,
            PayrollPeriod.end_date == end_date,
        )
        res = await db.execute(query)
        return res.unique().scalars().first()


class PayrollRecordRepository(BaseRepository[PayrollRecord, Any, Any]):
    """
    Repository layer for PayrollRecord entities.
    """

    def __init__(self):
        super().__init__(PayrollRecord)

    async def get_by_id(self, db: AsyncSession, id: uuid.UUID) -> Optional[PayrollRecord]:
        """Retrieves a PayrollRecord by ID with eagerly loaded components."""
        query = select(PayrollRecord).options(selectinload(PayrollRecord.components)).where(PayrollRecord.id == id)
        res = await db.execute(query)
        return res.unique().scalars().first()

    async def get_by_period_and_employee(
        self, db: AsyncSession, period_id: uuid.UUID, employee_id: uuid.UUID
    ) -> Optional[PayrollRecord]:
        """Retrieves a PayrollRecord by payroll_period_id and employee_id."""
        query = (
            select(PayrollRecord)
            .options(selectinload(PayrollRecord.components))
            .where(
                PayrollRecord.payroll_period_id == period_id,
                PayrollRecord.employee_id == employee_id,
            )
        )
        res = await db.execute(query)
        return res.unique().scalars().first()

    async def get_records_by_period(
        self, db: AsyncSession, period_id: uuid.UUID
    ) -> List[PayrollRecord]:
        """Retrieves all generated PayrollRecords for a payroll period with components, employee, and department."""
        query = (
            select(PayrollRecord)
            .options(
                selectinload(PayrollRecord.components),
                selectinload(PayrollRecord.employee).selectinload(Employee.department),
            )
            .where(PayrollRecord.payroll_period_id == period_id)
            .order_by(PayrollRecord.created_at)
        )
        res = await db.execute(query)
        return list(res.unique().scalars().all())

    async def get_employee_payroll_history(
        self, db: AsyncSession, employee_id: uuid.UUID
    ) -> List[PayrollRecord]:
        """Retrieves full payroll record history for an employee."""
        query = (
            select(PayrollRecord)
            .options(selectinload(PayrollRecord.components))
            .where(PayrollRecord.employee_id == employee_id)
            .order_by(PayrollRecord.created_at.desc())
        )
        res = await db.execute(query)
        return list(res.unique().scalars().all())


class PayrollRecordComponentRepository(BaseRepository[PayrollRecordComponent, Any, Any]):
    """
    Repository layer for PayrollRecordComponent line items.
    """

    def __init__(self):
        super().__init__(PayrollRecordComponent)

    async def get_components_by_record(
        self, db: AsyncSession, record_id: uuid.UUID
    ) -> List[PayrollRecordComponent]:
        """Retrieves component breakdown line items for a payroll record."""
        query = select(PayrollRecordComponent).where(
            PayrollRecordComponent.payroll_record_id == record_id
        )
        res = await db.execute(query)
        return list(res.unique().scalars().all())


payroll_period_repository = PayrollPeriodRepository()
payroll_record_repository = PayrollRecordRepository()
payroll_record_component_repository = PayrollRecordComponentRepository()
