from typing import Any, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_permission
from app.models.user import User
from app.schemas.finance import (
    AccountGroupCreate,
    AccountGroupResponse,
    AccountGroupUpdate,
    ChartOfAccountCreate,
    ChartOfAccountResponse,
    ChartOfAccountUpdate,
)
from app.services.finance_services import ChartOfAccountsService

router = APIRouter()
coa_service = ChartOfAccountsService()


# --- Account Groups ---
@router.post("/groups", response_model=AccountGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_account_group(
    obj_in: AccountGroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.accounts.create")),
) -> Any:
    try:
        return await coa_service.create_account_group(db, obj_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/groups/hierarchy", response_model=List[AccountGroupResponse])
async def get_account_group_hierarchy(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.accounts.read")),
) -> Any:
    return await coa_service.get_hierarchy(db)


# --- Chart of Accounts ---
@router.post("", response_model=ChartOfAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_chart_of_account(
    obj_in: ChartOfAccountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.accounts.create")),
) -> Any:
    try:
        return await coa_service.create_account(db, obj_in, current_user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[ChartOfAccountResponse])
async def list_chart_of_accounts(
    query: Optional[str] = Query(None),
    account_type: Optional[str] = Query(None),
    group_id: Optional[uuid.UUID] = Query(None),
    is_active: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.accounts.read")),
) -> Any:
    accounts, _ = await coa_service.account_repo.search_accounts(
        db, query=query, account_type=account_type, group_id=group_id, is_active=is_active, skip=skip, limit=limit
    )
    return accounts


@router.get("/{account_id}", response_model=ChartOfAccountResponse)
async def get_chart_of_account(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.accounts.read")),
) -> Any:
    account = await coa_service.account_repo.get_by_id(db, account_id)
    if not account or account.is_deleted:
        raise HTTPException(status_code=404, detail="Chart of Account not found")
    return account


@router.put("/{account_id}", response_model=ChartOfAccountResponse)
async def update_chart_of_account(
    account_id: uuid.UUID,
    obj_in: ChartOfAccountUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.accounts.update")),
) -> Any:
    try:
        return await coa_service.update_account(db, account_id, obj_in, current_user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chart_of_account(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.accounts.delete")),
) -> None:
    try:
        await coa_service.delete_account(db, account_id, current_user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
