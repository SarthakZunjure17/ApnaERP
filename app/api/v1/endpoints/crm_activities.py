import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.crm import ActivityCreate, ActivityResponse, ActivityUpdate
from app.services.crm_services import ActivityService

router = APIRouter()
act_service = ActivityService()


@router.post("", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
async def create_activity(
    act_in: ActivityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Log an Activity (Call, Email, Task, Follow-up)."""
    return await act_service.create_activity(db, act_in, current_user_id=current_user.id)


@router.get("", response_model=List[ActivityResponse])
async def list_activities(
    lead_id: Optional[uuid.UUID] = Query(None),
    opportunity_id: Optional[uuid.UUID] = Query(None),
    customer_id: Optional[uuid.UUID] = Query(None),
    campaign_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List Activities for an entity."""
    return await act_service.act_repo.get_by_entity(
        db, lead_id=lead_id, opportunity_id=opportunity_id, customer_id=customer_id, campaign_id=campaign_id
    )


@router.post("/{activity_id}/complete", response_model=ActivityResponse)
async def complete_activity(
    activity_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark an Activity as completed."""
    try:
        return await act_service.complete_activity(db, activity_id, current_user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
