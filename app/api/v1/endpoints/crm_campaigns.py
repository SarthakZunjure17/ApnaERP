import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.crm import (
    CampaignCreate,
    CampaignMemberCreate,
    CampaignMemberResponse,
    CampaignResponse,
    CampaignROIReport,
    CampaignUpdate,
)
from app.services.crm_services import CampaignService

router = APIRouter()
campaign_service = CampaignService()


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    camp_in: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a Marketing Campaign."""
    return await campaign_service.create_campaign(db, camp_in, current_user_id=current_user.id)


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get Campaign details."""
    camp = await campaign_service.campaign_repo.get_by_id(db, campaign_id)
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return camp


@router.post("/{campaign_id}/members", response_model=CampaignMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_campaign_member(
    campaign_id: uuid.UUID,
    member_in: CampaignMemberCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a member (Lead or Customer) to a Campaign."""
    return await campaign_service.add_member(db, campaign_id, member_in)


@router.get("/{campaign_id}/roi", response_model=CampaignROIReport)
async def get_campaign_roi(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Calculate Campaign ROI."""
    try:
        return await campaign_service.calculate_roi(db, campaign_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
