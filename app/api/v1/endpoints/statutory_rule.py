from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, has_permission
from app.models.user import User
from app.schemas.statutory_rule import (
    StatutoryCalculationRequest,
    StatutoryCalculationResponse,
    StatutoryRuleCreate,
    StatutoryRuleResponse,
    StatutoryRuleSlabCreate,
    StatutoryRuleSlabResponse,
    StatutoryRuleSlabUpdate,
    StatutoryRuleUpdate,
)
from app.services.statutory_compliance import StatutoryComplianceService
from app.utils.pagination import PaginatedResult, PaginationParams
from app.utils.sorting import parse_sort_query

router = APIRouter()


@router.get(
    "/statutory-rules",
    response_model=PaginatedResult[StatutoryRuleResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("statutory_rule.read"))],
)
async def list_statutory_rules(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    country_id: Optional[uuid.UUID] = Query(None),
    rule_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    sort: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves a paginated list of StatutoryRule records.
    """
    service = StatutoryComplianceService(db)
    pagination = PaginationParams(page=page, page_size=page_size)
    sorting = parse_sort_query(sort) if sort else None
    return await service.list_rules(
        params=pagination,
        country_id=country_id,
        rule_type=rule_type,
        is_active=is_active,
        search_term=search,
        sorting=sorting,
    )


@router.get(
    "/statutory-rules/{id}",
    response_model=StatutoryRuleResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("statutory_rule.read"))],
)
async def get_statutory_rule(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves a single StatutoryRule by ID with slabs and country info.
    """
    service = StatutoryComplianceService(db)
    return await service.get_rule_by_id(id=id)


@router.post(
    "/statutory-rules",
    response_model=StatutoryRuleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("statutory_rule.create"))],
)
async def create_statutory_rule(
    data: StatutoryRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Creates a new StatutoryRule with optional initial slabs.
    """
    service = StatutoryComplianceService(db)
    return await service.create_rule(data=data, current_user=current_user)


@router.put(
    "/statutory-rules/{id}",
    response_model=StatutoryRuleResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("statutory_rule.update"))],
)
async def update_statutory_rule(
    id: uuid.UUID,
    data: StatutoryRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Updates an existing StatutoryRule.
    """
    service = StatutoryComplianceService(db)
    return await service.update_rule(id=id, data=data, current_user=current_user)


@router.delete(
    "/statutory-rules/{id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("statutory_rule.delete"))],
)
async def delete_statutory_rule(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Soft deletes a StatutoryRule.
    """
    service = StatutoryComplianceService(db)
    await service.delete_rule(id=id, current_user=current_user)
    return {"message": "StatutoryRule successfully deleted."}


# --- Slabs ---

@router.post(
    "/statutory-rules/{id}/slabs",
    response_model=StatutoryRuleSlabResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("statutory_rule.update"))],
)
async def add_rule_slab(
    id: uuid.UUID,
    data: StatutoryRuleSlabCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Adds a new slab boundary to a StatutoryRule.
    """
    service = StatutoryComplianceService(db)
    return await service.add_rule_slab(rule_id=id, data=data, current_user=current_user)


@router.put(
    "/statutory-rules/slabs/{id}",
    response_model=StatutoryRuleSlabResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("statutory_rule.update"))],
)
async def update_rule_slab(
    id: uuid.UUID,
    data: StatutoryRuleSlabUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Updates an existing StatutoryRuleSlab.
    """
    service = StatutoryComplianceService(db)
    return await service.update_rule_slab(slab_id=id, data=data, current_user=current_user)


@router.delete(
    "/statutory-rules/slabs/{id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("statutory_rule.update"))],
)
async def delete_rule_slab(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Deletes a StatutoryRuleSlab.
    """
    service = StatutoryComplianceService(db)
    await service.delete_rule_slab(slab_id=id, current_user=current_user)
    return {"message": "StatutoryRuleSlab successfully deleted."}


# --- Engine Calculation ---

@router.post(
    "/statutory-rules/calculate",
    response_model=StatutoryCalculationResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("statutory_rule.read"))],
)
async def calculate_statutory_deductions(
    data: StatutoryCalculationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Executes Statutory Compliance Engine to compute statutory deductions for an employee.
    """
    service = StatutoryComplianceService(db)
    return await service.calculate_statutory_deductions(
        employee_id=data.employee_id,
        gross_salary=data.gross_salary,
        calculation_date=data.calculation_date,
    )
