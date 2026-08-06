import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.crm import (
    OpportunityCreate,
    OpportunityResponse,
    OpportunityStageCreate,
    OpportunityStageResponse,
    OpportunityUpdate,
    OpportunityWinLossRequest,
)
from app.services.crm_services import OpportunityService

router = APIRouter()
opp_service = OpportunityService()


@router.post("/stages", response_model=OpportunityStageResponse, status_code=status.HTTP_201_CREATED)
async def create_stage(
    stage_in: OpportunityStageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create an Opportunity Pipeline Stage."""
    stage = await opp_service.stage_repo.create(db, stage_in)
    return stage


@router.get("/stages", response_model=List[OpportunityStageResponse])
async def list_stages(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List Opportunity Pipeline Stages."""
    return await opp_service.stage_repo.get_all_ordered(db)


@router.post("", response_model=OpportunityResponse, status_code=status.HTTP_201_CREATED)
async def create_opportunity(
    opp_in: OpportunityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new Opportunity."""
    try:
        return await opp_service.create_opportunity(db, opp_in, current_user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[OpportunityResponse])
async def list_opportunities(
    query: Optional[str] = Query(None),
    stage_id: Optional[uuid.UUID] = Query(None),
    customer_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    owner_id: Optional[uuid.UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search and filter Opportunities."""
    opps, _ = await opp_service.opp_repo.search_opportunities(
        db, query=query, stage_id=stage_id, customer_id=customer_id, status=status, owner_id=owner_id, skip=skip, limit=limit
    )
    return opps


@router.get("/{opp_id}", response_model=OpportunityResponse)
async def get_opportunity(
    opp_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get Opportunity by ID."""
    opp = await opp_service.opp_repo.get_by_id(db, opp_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return opp


@router.put("/{opp_id}", response_model=OpportunityResponse)
async def update_opportunity(
    opp_id: uuid.UUID,
    opp_in: OpportunityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update Opportunity details."""
    try:
        return await opp_service.update_opportunity(db, opp_id, opp_in, current_user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{opp_id}/win-loss", response_model=OpportunityResponse)
async def record_win_loss(
    opp_id: uuid.UUID,
    req: OpportunityWinLossRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record Opportunity Win or Loss."""
    try:
        return await opp_service.record_win_loss(db, opp_id, req.status, reason=req.reason, current_user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
