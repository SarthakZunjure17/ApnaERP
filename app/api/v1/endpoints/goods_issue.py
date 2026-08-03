from datetime import datetime
from typing import Any, Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission
from app.models.user import User
from app.schemas.warehouse_operations import (
    GoodsIssueCreate,
    GoodsIssueResponse,
    GoodsIssueUpdate,
    PaginatedGoodsIssueResponse,
)
from app.services.warehouse_operations_services import goods_issue_service

router = APIRouter()


@router.post(
    "",
    response_model=GoodsIssueResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Draft Goods Issue",
)
async def create_goods_issue(
    obj_in: GoodsIssueCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.issue.create")),
) -> Any:
    return await goods_issue_service.create_issue(db, obj_in, current_user_id=current_user.id)


@router.get(
    "",
    response_model=PaginatedGoodsIssueResponse,
    summary="List Goods Issues with pagination and filters",
)
async def list_goods_issues(
    warehouse_id: Optional[uuid.UUID] = Query(None, description="Filter by warehouse ID"),
    status: Optional[str] = Query(None, description="Filter by document status: Draft, Issued, Cancelled"),
    issue_reason: Optional[str] = Query(None, description="Filter by reason: Consumption, Internal, Damage, Sample, Adjustment, Other"),
    start_date: Optional[datetime] = Query(None, description="Filter by start issue date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end issue date"),
    search: Optional[str] = Query(None, description="Search term for issue number or reason"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.issue.read")),
) -> Any:
    items, total = await goods_issue_service.get_issues(
        db, warehouse_id=warehouse_id, status=status, issue_reason=issue_reason, start_date=start_date, end_date=end_date, search=search, skip=skip, limit=limit
    )
    return PaginatedGoodsIssueResponse(items=items, total=total, skip=skip, limit=limit)


@router.get(
    "/{id}",
    response_model=GoodsIssueResponse,
    summary="Get Goods Issue details by ID",
)
async def get_goods_issue(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.issue.read")),
) -> Any:
    return await goods_issue_service.get_issue(db, id)


@router.put(
    "/{id}",
    response_model=GoodsIssueResponse,
    summary="Update a Draft Goods Issue",
)
async def update_goods_issue(
    id: uuid.UUID,
    obj_in: GoodsIssueUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.issue.update")),
) -> Any:
    return await goods_issue_service.update_issue(db, id, obj_in, current_user_id=current_user.id)


@router.post(
    "/{id}/approve",
    response_model=GoodsIssueResponse,
    summary="Approve a Draft Goods Issue document",
)
async def approve_goods_issue(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.issue.approve")),
) -> Any:
    return await goods_issue_service.approve_issue(db, id, current_user_id=current_user.id)


@router.post(
    "/{id}/issue",
    response_model=GoodsIssueResponse,
    summary="Issue/Execute Goods Issue and generate Stock Ledger OUT entries",
)
async def issue_goods_issue(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.issue.issue")),
) -> Any:
    return await goods_issue_service.issue_issue(db, id, current_user_id=current_user.id)


@router.post(
    "/{id}/cancel",
    response_model=GoodsIssueResponse,
    summary="Cancel a Goods Issue document",
)
async def cancel_goods_issue(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("inventory.issue.cancel")),
) -> Any:
    return await goods_issue_service.cancel_issue(db, id, current_user_id=current_user.id)
