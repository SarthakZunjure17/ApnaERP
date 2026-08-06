from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_permission
from app.models.user import User
from app.schemas.finance import FinanceSearchResponse
from app.services.finance_services import ChartOfAccountsService, CostCenterService, JournalService

router = APIRouter()
coa_service = ChartOfAccountsService()
journal_service = JournalService()
cc_service = CostCenterService()


@router.get("", response_model=FinanceSearchResponse)
async def search_finance(
    query: str = Query(..., min_length=2),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.accounts.read")),
) -> Any:
    accounts, _ = await coa_service.account_repo.search_accounts(db, query=query, limit=20)
    journals, _ = await journal_service.journal_repo.search_journals(db, query=query, limit=20)
    cost_centers = await cc_service.cost_repo.get_all(db)
    filtered_ccs = [cc for cc in cost_centers if query.lower() in cc.name.lower() or query.lower() in cc.code.lower()]

    return FinanceSearchResponse(
        accounts=accounts,
        journals=journals,
        cost_centers=filtered_ccs,
    )
