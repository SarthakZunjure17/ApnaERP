from typing import List, Optional
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial_posting_queue import FinancialPostingQueue
from app.models.payroll_closing import PayrollClosing
from app.models.payroll_report_snapshot import PayrollReportSnapshot
from app.repositories.base_repository import BaseRepository
from app.utils.pagination import PaginatedResult, PaginationParams
from app.utils.sorting import SortCriterion, SortOrder, apply_sorting


class PayrollReportSnapshotRepository(BaseRepository[PayrollReportSnapshot, None, None]):
    """
    Repository for managing PayrollReportSnapshot entities.
    """
    def __init__(self):
        super().__init__(PayrollReportSnapshot)

    async def get_filtered_snapshots(
        self,
        db: AsyncSession,
        params: PaginationParams,
        payroll_period_id: Optional[uuid.UUID] = None,
        report_type: Optional[str] = None,
        sorting: Optional[List[SortCriterion]] = None,
    ) -> PaginatedResult[PayrollReportSnapshot]:
        query = select(PayrollReportSnapshot)
        if payroll_period_id:
            query = query.where(PayrollReportSnapshot.payroll_period_id == payroll_period_id)
        if report_type:
            query = query.where(PayrollReportSnapshot.report_type == report_type)

        default_sort = [SortCriterion(field="generated_at", order=SortOrder.DESC)]
        query = apply_sorting(query, PayrollReportSnapshot, sorting if sorting else default_sort)

        count_query = select(func.count()).select_from(query.subquery())
        total_res = await db.execute(count_query)
        total = total_res.scalar_one()

        query = query.offset((params.page - 1) * params.page_size).limit(params.page_size)
        results = await db.execute(query)
        items = list(results.unique().scalars().all())

        return PaginatedResult(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
        )


class PayrollClosingRepository(BaseRepository[PayrollClosing, None, None]):
    """
    Repository for managing PayrollClosing entities.
    """
    def __init__(self):
        super().__init__(PayrollClosing)

    async def get_by_period_id(
        self,
        db: AsyncSession,
        payroll_period_id: uuid.UUID,
    ) -> Optional[PayrollClosing]:
        query = select(PayrollClosing).where(PayrollClosing.payroll_period_id == payroll_period_id)
        res = await db.execute(query)
        return res.unique().scalars().first()


class FinancialPostingQueueRepository(BaseRepository[FinancialPostingQueue, None, None]):
    """
    Repository for managing FinancialPostingQueue entities.
    """
    def __init__(self):
        super().__init__(FinancialPostingQueue)

    async def get_by_period_id(
        self,
        db: AsyncSession,
        payroll_period_id: uuid.UUID,
    ) -> List[FinancialPostingQueue]:
        query = select(FinancialPostingQueue).where(FinancialPostingQueue.payroll_period_id == payroll_period_id)
        res = await db.execute(query)
        return list(res.unique().scalars().all())

    async def get_pending_postings(
        self,
        db: AsyncSession,
    ) -> List[FinancialPostingQueue]:
        query = select(FinancialPostingQueue).where(FinancialPostingQueue.posting_status == "Pending")
        res = await db.execute(query)
        return list(res.unique().scalars().all())
