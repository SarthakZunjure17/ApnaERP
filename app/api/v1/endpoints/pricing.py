from typing import List
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_permission
from app.models.user import User
from app.schemas.sales import (
    PriceListCreate,
    PriceListResponse,
    PricingRuleCreate,
    PricingRuleResponse,
)
from app.services.pricing_services import pricing_service

router = APIRouter()


@router.post("/price-lists", response_model=PriceListResponse, status_code=status.HTTP_201_CREATED)
async def create_price_list(
    obj_in: PriceListCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.pricing.create")),
):
    return await pricing_service.create_price_list(db, obj_in)


@router.get("/price-lists", response_model=List[PriceListResponse])
async def list_price_lists(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.pricing.read")),
):
    return await pricing_service.list_price_lists(db)


@router.get("/price-lists/{price_list_id}", response_model=PriceListResponse)
async def get_price_list(
    price_list_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.pricing.read")),
):
    return await pricing_service.get_price_list(db, price_list_id)


@router.post("/rules", response_model=PricingRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_pricing_rule(
    obj_in: PricingRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("sales.pricing.create")),
):
    return await pricing_service.create_pricing_rule(db, obj_in)
