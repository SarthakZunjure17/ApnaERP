from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_permission
from app.models.user import User
from app.schemas.sales import DiscountRuleCreate, DiscountRuleResponse
from app.services.pricing_services import discount_service

router = APIRouter()


@router.post("/rules", response_model=DiscountRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_discount_rule(
    obj_in: DiscountRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.pricing.create")),
):
    return await discount_service.create_discount_rule(db, obj_in)


@router.get("/rules", response_model=List[DiscountRuleResponse])
async def list_discount_rules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.pricing.read")),
):
    return await discount_service.list_discount_rules(db)
