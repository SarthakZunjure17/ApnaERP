from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_permission
from app.models.user import User
from app.schemas.finance import PostingRuleCreate, PostingRuleResponse
from app.services.finance_services import PostingRuleService

router = APIRouter()
rule_service = PostingRuleService()


@router.post("", response_model=PostingRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_posting_rule(
    obj_in: PostingRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.posting.create")),
) -> Any:
    try:
        return await rule_service.create_posting_rule(db, obj_in, current_user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[PostingRuleResponse])
async def list_posting_rules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.posting.read")),
) -> Any:
    return await rule_service.rule_repo.get_all(db)
