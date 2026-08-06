from datetime import datetime
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.crm import MeetingCreate, MeetingResponse, MeetingUpdate
from app.services.crm_services import MeetingService

router = APIRouter()
meeting_service = MeetingService()


@router.post("", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def schedule_meeting(
    meeting_in: MeetingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Schedule a Meeting / Customer Visit / Sales Call."""
    return await meeting_service.schedule_meeting(db, meeting_in, current_user_id=current_user.id)


@router.get("", response_model=List[MeetingResponse])
async def list_meetings(
    lead_id: Optional[uuid.UUID] = Query(None),
    opportunity_id: Optional[uuid.UUID] = Query(None),
    customer_id: Optional[uuid.UUID] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List Meetings for Calendar."""
    return await meeting_service.meeting_repo.get_by_entity_or_date(
        db, lead_id=lead_id, opportunity_id=opportunity_id, customer_id=customer_id, start_date=start_date, end_date=end_date
    )
