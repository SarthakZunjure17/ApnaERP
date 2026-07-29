import logging
from typing import Any, List, Optional
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.payslip import Payslip
from app.repositories.base_repository import BaseRepository
from app.utils.pagination import PaginatedResult, PaginationParams
from app.utils.sorting import SortCriterion, SortOrder, apply_sorting

logger = logging.getLogger("app.repositories.payslip")


class PayslipRepository(BaseRepository[Payslip, Any, Any]):
    """
    Repository layer for Payslip entity database interactions.
    """

    def __init__(self):
        super().__init__(Payslip)

    async def get_by_payslip_number(self, db: AsyncSession, payslip_number: str) -> Optional[Payslip]:
        """Retrieves a Payslip by its unique payslip_number."""
        query = select(Payslip).options(
            selectinload(Payslip.employee),
            selectinload(Payslip.payroll_period),
            selectinload(Payslip.pdf_file),
            selectinload(Payslip.payroll_record),
        ).where(Payslip.payslip_number == payslip_number)
        res = await db.execute(query)
        return res.unique().scalars().first()

    async def get_by_payroll_record_id(self, db: AsyncSession, record_id: uuid.UUID) -> Optional[Payslip]:
        """Retrieves a Payslip by payroll_record_id."""
        query = select(Payslip).options(
            selectinload(Payslip.employee),
            selectinload(Payslip.payroll_period),
            selectinload(Payslip.pdf_file),
            selectinload(Payslip.payroll_record),
        ).where(Payslip.payroll_record_id == record_id)
        res = await db.execute(query)
        return res.unique().scalars().first()

    async def get_by_employee_id(
        self, db: AsyncSession, employee_id: uuid.UUID
    ) -> List[Payslip]:
        """Retrieves all payslips for an employee ordered by created_at DESC."""
        query = (
            select(Payslip)
            .options(
                selectinload(Payslip.employee),
                selectinload(Payslip.payroll_period),
                selectinload(Payslip.pdf_file),
            )
            .where(Payslip.employee_id == employee_id)
            .order_by(Payslip.created_at.desc())
        )
        res = await db.execute(query)
        return list(res.unique().scalars().all())

    async def get_by_period_id(
        self, db: AsyncSession, period_id: uuid.UUID
    ) -> List[Payslip]:
        """Retrieves all payslips for a payroll period."""
        query = (
            select(Payslip)
            .options(
                selectinload(Payslip.employee),
                selectinload(Payslip.payroll_period),
                selectinload(Payslip.pdf_file),
            )
            .where(Payslip.payroll_period_id == period_id)
        )
        res = await db.execute(query)
        return list(res.unique().scalars().all())

    async def get_filtered_payslips(
        self,
        db: AsyncSession,
        *,
        params: PaginationParams,
        employee_id: Optional[uuid.UUID] = None,
        period_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        search_term: Optional[str] = None,
        sorting: Optional[List[SortCriterion]] = None,
    ) -> PaginatedResult[Payslip]:
        """
        Queries Payslip records with filtering, pagination, sorting, and relationship loading.
        """
        query = select(Payslip).options(
            selectinload(Payslip.employee),
            selectinload(Payslip.payroll_period),
            selectinload(Payslip.pdf_file),
        )

        if employee_id:
            query = query.where(Payslip.employee_id == employee_id)
        if period_id:
            query = query.where(Payslip.payroll_period_id == period_id)
        if status:
            query = query.where(Payslip.status == status)
        if search_term:
            term = f"%{search_term}%"
            query = query.where(Payslip.payslip_number.ilike(term))

        # Apply sorting
        default_sort = [SortCriterion(field="created_at", order=SortOrder.DESC)]
        query = apply_sorting(query, Payslip, sorting if sorting else default_sort)

        # Count total records
        count_query = select(func.count()).select_from(query.subquery())
        total_res = await db.execute(count_query)
        total = total_res.scalar_one()

        # Apply pagination
        query = query.offset((params.page - 1) * params.page_size).limit(params.page_size)
        results = await db.execute(query)
        items = list(results.unique().scalars().all())

        return PaginatedResult(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
        )


payslip_repository = PayslipRepository()
