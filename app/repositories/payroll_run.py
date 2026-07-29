import logging
from typing import Any, List, Optional
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.payroll_run import PayrollRun
from app.repositories.base_repository import BaseRepository
from app.utils.pagination import PaginatedResult, PaginationParams
from app.utils.sorting import SortCriterion, SortOrder, apply_sorting

logger = logging.getLogger("app.repositories.payroll_run")


class PayrollRunRepository(BaseRepository[PayrollRun, Any, Any]):
    """
    Repository layer for PayrollRun entity database interactions.
    """

    def __init__(self):
        super().__init__(PayrollRun)

    async def get_by_run_number(self, db: AsyncSession, run_number: str) -> Optional[PayrollRun]:
        """Retrieves a PayrollRun by its unique run_number."""
        query = select(PayrollRun).options(selectinload(PayrollRun.payroll_period)).where(PayrollRun.run_number == run_number)
        res = await db.execute(query)
        return res.unique().scalars().first()

    async def get_by_period_and_type(
        self, db: AsyncSession, period_id: uuid.UUID, run_type: str
    ) -> Optional[PayrollRun]:
        """Retrieves a PayrollRun by payroll_period_id and run_type."""
        query = select(PayrollRun).where(
            PayrollRun.payroll_period_id == period_id,
            PayrollRun.run_type == run_type,
        )
        res = await db.execute(query)
        return res.unique().scalars().first()

    async def get_filtered_runs(
        self,
        db: AsyncSession,
        *,
        params: PaginationParams,
        period_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        run_type: Optional[str] = None,
        search_term: Optional[str] = None,
        sorting: Optional[List[SortCriterion]] = None,
    ) -> PaginatedResult[PayrollRun]:
        """
        Queries PayrollRun records with filtering, pagination, sorting, and period loading.
        """
        query = select(PayrollRun).options(selectinload(PayrollRun.payroll_period))

        if period_id:
            query = query.where(PayrollRun.payroll_period_id == period_id)
        if status:
            query = query.where(PayrollRun.status == status)
        if run_type:
            query = query.where(PayrollRun.run_type == run_type)
        if search_term:
            term = f"%{search_term}%"
            query = query.where(
                PayrollRun.run_number.ilike(term) | PayrollRun.remarks.ilike(term)
            )

        # Apply sorting
        default_sort = [SortCriterion(field="created_at", order=SortOrder.DESC)]
        query = apply_sorting(query, PayrollRun, sorting if sorting else default_sort)

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


payroll_run_repository = PayrollRunRepository()
