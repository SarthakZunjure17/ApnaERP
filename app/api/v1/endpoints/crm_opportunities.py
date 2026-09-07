import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_permission
from app.exceptions.base import NotFoundException, ValidationException
from app.models.user import User
from app.schemas.crm import (
    OpportunityCreate,
    OpportunityResponse,
    OpportunityStageChangeRequest,
    OpportunityStageCreate,
    OpportunityStageResponse,
    OpportunityUpdate,
    OpportunityWinLossRequest,
)
from app.services.crm_services import opportunity_service

router = APIRouter()


@router.post("/stages", response_model=OpportunityStageResponse, status_code=status.HTTP_201_CREATED)
async def create_stage(
    stage_in: OpportunityStageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("crm.opportunity.stage")),
):
    """Create an Opportunity Pipeline Stage."""
    stage = await opportunity_service.stage_repo.create(db, stage_in)
    return stage


@router.get("/stages", response_model=List[OpportunityStageResponse])
async def list_stages(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("crm.opportunity.read")),
):
    """List Opportunity Pipeline Stages."""
    return await opportunity_service.stage_repo.get_all_ordered(db)


@router.post("", response_model=OpportunityResponse, status_code=status.HTTP_201_CREATED)
async def create_opportunity(
    opp_in: OpportunityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("crm.opportunity.create")),
):
    """Create a new Opportunity."""
    try:
        return await opportunity_service.create_opportunity(db, opp_in, current_user_id=current_user.id)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (ValidationException, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[OpportunityResponse])
async def list_opportunities(
    query: Optional[str] = Query(None),
    stage_id: Optional[uuid.UUID] = Query(None),
    customer_id: Optional[uuid.UUID] = Query(None),
    lead_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    owner_id: Optional[uuid.UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("crm.opportunity.read")),
):
    """Search and filter Opportunities."""
    opps, _ = await opportunity_service.opp_repo.search_opportunities(
        db,
        query=query,
        stage_id=stage_id,
        customer_id=customer_id,
        lead_id=lead_id,
        status=status,
        owner_id=owner_id,
        skip=skip,
        limit=limit,
    )
    return opps


@router.get("/{opp_id}", response_model=OpportunityResponse)
async def get_opportunity(
    opp_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("crm.opportunity.read")),
):
    """Get Opportunity by ID."""
    opp = await opportunity_service.opp_repo.get_by_id(db, opp_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return opp


@router.put("/{opp_id}", response_model=OpportunityResponse)
async def update_opportunity(
    opp_id: uuid.UUID,
    opp_in: OpportunityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("crm.opportunity.update")),
):
    """Update Opportunity details."""
    try:
        return await opportunity_service.update_opportunity(db, opp_id, opp_in, current_user_id=current_user.id)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (ValidationException, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{opp_id}", response_model=OpportunityResponse)
async def patch_opportunity(
    opp_id: uuid.UUID,
    opp_in: OpportunityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("crm.opportunity.update")),
):
    """Patch Opportunity details."""
    try:
        return await opportunity_service.update_opportunity(db, opp_id, opp_in, current_user_id=current_user.id)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (ValidationException, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{opp_id}", status_code=status.HTTP_200_OK)
async def delete_opportunity(
    opp_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("crm.opportunity.delete")),
):
    """Soft delete an Opportunity."""
    try:
        await opportunity_service.delete_opportunity(db, opp_id, current_user_id=current_user.id)
        return {"detail": "Opportunity deleted successfully"}
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (ValidationException, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{opp_id}/stage", response_model=OpportunityResponse)
async def change_stage(
    opp_id: uuid.UUID,
    req: OpportunityStageChangeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("crm.opportunity.stage")),
):
    """Advance or change Opportunity Pipeline Stage."""
    try:
        return await opportunity_service.change_stage(db, opp_id, req, current_user_id=current_user.id)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (ValidationException, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{opp_id}/win-loss", response_model=OpportunityResponse)
async def record_win_loss(
    opp_id: uuid.UUID,
    req: OpportunityWinLossRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("crm.opportunity.update")),
):
    """Record Opportunity Win or Loss."""
    try:
        return await opportunity_service.record_win_loss(db, opp_id, req.status, reason=req.reason, current_user_id=current_user.id)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (ValidationException, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
