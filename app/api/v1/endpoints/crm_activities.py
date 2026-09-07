import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_permission
from app.exceptions.base import NotFoundException, ValidationException
from app.models.user import User
from app.schemas.crm import ActivityCreate, ActivityResponse, ActivityUpdate
from app.services.crm_services import activity_service

router = APIRouter()


@router.post("", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
async def create_activity(
    act_in: ActivityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("crm.activity.create")),
):
    """Log an Activity (Call, Meeting, Email, Note, Follow-up)."""
    try:
        return await activity_service.create_activity(db, act_in, current_user_id=current_user.id)
    except (ValidationException, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[ActivityResponse])
async def list_activities(
    query: Optional[str] = Query(None),
    activity_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    lead_id: Optional[uuid.UUID] = Query(None),
    opportunity_id: Optional[uuid.UUID] = Query(None),
    customer_id: Optional[uuid.UUID] = Query(None),
    owner_id: Optional[uuid.UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("crm.activity.read")),
):
    """List Activities with search and entity filters."""
    acts, _ = await activity_service.act_repo.search_activities(
        db,
        query=query,
        activity_type=activity_type,
        status=status,
        owner_id=owner_id,
        lead_id=lead_id,
        opportunity_id=opportunity_id,
        customer_id=customer_id,
        skip=skip,
        limit=limit,
    )
    return acts


@router.get("/{activity_id}", response_model=ActivityResponse)
async def get_activity(
    activity_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("crm.activity.read")),
):
    """Get Activity by ID."""
    activity = await activity_service.act_repo.get_by_id(db, activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity


@router.put("/{activity_id}", response_model=ActivityResponse)
async def update_activity(
    activity_id: uuid.UUID,
    act_in: ActivityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("crm.activity.update")),
):
    """Update Activity details."""
    try:
        return await activity_service.update_activity(db, activity_id, act_in, current_user_id=current_user.id)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (ValidationException, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{activity_id}", response_model=ActivityResponse)
async def patch_activity(
    activity_id: uuid.UUID,
    act_in: ActivityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("crm.activity.update")),
):
    """Patch Activity details."""
    try:
        return await activity_service.update_activity(db, activity_id, act_in, current_user_id=current_user.id)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (ValidationException, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{activity_id}/complete", response_model=ActivityResponse)
async def complete_activity(
    activity_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("crm.activity.update")),
):
    """Mark an Activity as completed."""
    try:
        return await activity_service.complete_activity(db, activity_id, current_user_id=current_user.id)
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (ValidationException, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{activity_id}", status_code=status.HTTP_200_OK)
async def delete_activity(
    activity_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("crm.activity.delete")),
):
    """Delete an Activity."""
    try:
        await activity_service.delete_activity(db, activity_id, current_user_id=current_user.id)
        return {"detail": "Activity deleted successfully"}
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (ValidationException, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
