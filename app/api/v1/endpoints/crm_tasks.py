import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.crm import TaskCreate, TaskResponse, TaskUpdate
from app.services.crm_services import TaskService

router = APIRouter()
task_service = TaskService()


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_in: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a Task."""
    return await task_service.create_task(db, task_in, current_user_id=current_user.id)


@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    query: Optional[str] = Query(None),
    assigned_to_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List Tasks."""
    tasks, _ = await task_service.task_repo.search_tasks(
        db, query=query, assigned_to_id=assigned_to_id, status=status, priority=priority, skip=skip, limit=limit
    )
    return tasks


@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a Task as completed."""
    try:
        return await task_service.complete_task(db, task_id, current_user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
