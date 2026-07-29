from typing import List, Optional
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payroll_adjustment import PayrollAdjustment
from app.repositories.base_repository import BaseRepository
from app.utils.pagination import PaginatedResult, PaginationParams
from app.utils.sorting import SortCriterion, SortOrder, apply_sorting


class PayrollAdjustmentRepository(BaseRepository[PayrollAdjustment, None, None]):
    """
    Repository for managing PayrollAdjustment entities.
    """
    def __init__(self):
        super().__init__(PayrollAdjustment)

    async def get_filtered_adjustments(
        self,
        db: AsyncSession,
        params: PaginationParams,
        payroll_period_id: Optional[uuid.UUID] = None,
        employee_id: Optional[uuid.UUID] = None,
        adjustment_type: Optional[str] = None,
        status: Optional[str] = None,
        sorting: Optional[List[SortCriterion]] = None,
    ) -> PaginatedResult[PayrollAdjustment]:
        query = select(PayrollAdjustment)

        if payroll_period_id:
            query = query.where(PayrollAdjustment.payroll_period_id == payroll_period_id)
        if employee_id:
            query = query.where(PayrollAdjustment.employee_id == employee_id)
        if adjustment_type:
            query = query.where(PayrollAdjustment.adjustment_type == adjustment_type)
        if status:
            query = query.where(PayrollAdjustment.status == status)

        default_sort = [SortCriterion(field="created_at", order=SortOrder.DESC)]
        query = apply_sorting(query, PayrollAdjustment, sorting if sorting else default_sort)

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

    async def get_approved_adjustments_for_period(
        self,
        db: AsyncSession,
        payroll_period_id: uuid.UUID,
        employee_id: Optional[uuid.UUID] = None,
    ) -> List[PayrollAdjustment]:
        query = select(PayrollAdjustment).where(
            PayrollAdjustment.payroll_period_id == payroll_period_id,
            PayrollAdjustment.status == "Approved",
        )
        if employee_id:
            query = query.where(PayrollAdjustment.employee_id == employee_id)
        res = await db.execute(query)
        return list(res.unique().scalars().all())
