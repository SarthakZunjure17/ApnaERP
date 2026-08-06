from typing import List
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.finance_ops import (
    AssetCategoryCreate,
    AssetCategoryResponse,
    DepreciationScheduleResponse,
    FixedAssetCreate,
    FixedAssetResponse,
)
from app.services.finance_ops_services import AssetService, DepreciationService

router = APIRouter()


@router.post("/categories", response_model=AssetCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_asset_category(
    data: AssetCategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AssetService(db)
    return await service.create_category(data)


@router.post("/fixed-assets", response_model=FixedAssetResponse, status_code=status.HTTP_201_CREATED)
async def create_fixed_asset(
    data: FixedAssetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AssetService(db)
    return await service.create_asset(data, current_user)


@router.post("/fixed-assets/{asset_id}/schedule", response_model=List[DepreciationScheduleResponse])
async def generate_depreciation_schedule(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = DepreciationService(db)
    return await service.generate_schedule(asset_id)


@router.post("/schedules/{schedule_id}/post", response_model=DepreciationScheduleResponse)
async def post_depreciation_entry(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = DepreciationService(db)
    return await service.post_depreciation(schedule_id, current_user)
