from datetime import date
from typing import Any, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_permission
from app.models.user import User
from app.schemas.finance import (
    JournalCreate,
    JournalResponse,
    JournalReverseRequest,
    JournalTypeCreate,
    JournalTypeResponse,
)
from app.services.finance_services import JournalService, PostingEngineService

router = APIRouter()
journal_service = JournalService()
posting_engine = PostingEngineService()


# --- Journal Types ---
@router.post("/types", response_model=JournalTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_journal_type(
    obj_in: JournalTypeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.journal.create")),
) -> Any:
    try:
        return await journal_service.create_journal_type(db, obj_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/types", response_model=List[JournalTypeResponse])
async def list_journal_types(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.journal.read")),
) -> Any:
    return await journal_service.type_repo.get_all(db)


# --- Journals ---
@router.post("", response_model=JournalResponse, status_code=status.HTTP_201_CREATED)
async def create_journal(
    obj_in: JournalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.journal.create")),
) -> Any:
    try:
        return await journal_service.create_journal(db, obj_in, current_user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[JournalResponse])
async def list_journals(
    query: Optional[str] = Query(None),
    journal_type_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.journal.read")),
) -> Any:
    journals, _ = await journal_service.journal_repo.search_journals(
        db,
        query=query,
        journal_type_id=journal_type_id,
        status=status,
        from_date=from_date,
        to_date=to_date,
        skip=skip,
        limit=limit,
    )
    return journals


@router.get("/{journal_id}", response_model=JournalResponse)
async def get_journal(
    journal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.journal.read")),
) -> Any:
    journal = await journal_service.journal_repo.get_by_id_with_details(db, journal_id)
    if not journal:
        raise HTTPException(status_code=404, detail="Journal not found")
    return journal


@router.post("/{journal_id}/post", response_model=JournalResponse)
async def post_journal(
    journal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.journal.post")),
) -> Any:
    try:
        return await posting_engine.post_journal(db, journal_id, current_user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{journal_id}/reverse", response_model=JournalResponse)
async def reverse_journal(
    journal_id: uuid.UUID,
    req: JournalReverseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.journal.reverse")),
) -> Any:
    try:
        return await posting_engine.reverse_journal(
            db, journal_id, reversal_reason=req.reason, current_user_id=current_user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{journal_id}/cancel", response_model=JournalResponse)
async def cancel_journal(
    journal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("finance.journal.cancel")),
) -> Any:
    try:
        return await journal_service.cancel_journal(db, journal_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
