import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.crm import (
    LeadConversionRequest,
    LeadConversionResponse,
    LeadCreate,
    LeadMergeRequest,
    LeadNoteCreate,
    LeadNoteResponse,
    LeadResponse,
    LeadUpdate,
)
from app.services.crm_services import LeadConversionService, LeadService

router = APIRouter()
lead_service = LeadService()
conversion_service = LeadConversionService()


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    lead_in: LeadCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new Lead."""
    return await lead_service.create_lead(db, lead_in, current_user_id=current_user.id)


@router.get("", response_model=List[LeadResponse])
async def list_leads(
    query: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    assigned_to_id: Optional[uuid.UUID] = Query(None),
    is_converted: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search and filter Leads."""
    leads, _ = await lead_service.lead_repo.search_leads(
        db, query=query, status=status, assigned_to_id=assigned_to_id, is_converted=is_converted, skip=skip, limit=limit
    )
    return leads


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get Lead by ID."""
    lead = await lead_service.lead_repo.get_by_id(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.put("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: uuid.UUID,
    lead_in: LeadUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update Lead details."""
    try:
        return await lead_service.update_lead(db, lead_id, lead_in, current_user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{lead_id}/assign", response_model=LeadResponse)
async def assign_lead(
    lead_id: uuid.UUID,
    assigned_to_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Assign Lead to a sales representative."""
    try:
        return await lead_service.assign_lead(db, lead_id, assigned_to_id, current_user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{lead_id}/notes", response_model=LeadNoteResponse, status_code=status.HTTP_201_CREATED)
async def add_lead_note(
    lead_id: uuid.UUID,
    note_in: LeadNoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add note to Lead."""
    return await lead_service.add_note(db, lead_id, note_in, author_id=current_user.id)


@router.post("/merge", response_model=LeadResponse)
async def merge_leads(
    merge_in: LeadMergeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Merge duplicate leads into a primary lead."""
    try:
        return await lead_service.merge_leads(db, merge_in, current_user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/convert", response_model=LeadConversionResponse)
async def convert_lead(
    req: LeadConversionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Convert Lead to Opportunity and link to existing or new Customer."""
    try:
        return await conversion_service.convert_lead(db, req, current_user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
