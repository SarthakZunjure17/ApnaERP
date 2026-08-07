from typing import Any, Dict, List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.reporting import ScheduledReportCreate, ScheduledReportResponse
from app.services.reporting_services import ScheduledReportService

router = APIRouter()


@router.get("/", response_model=List[ScheduledReportResponse])
async def list_scheduled_reports(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = ScheduledReportService(db)
    return await service.sched_repo.get_due_schedules(db)


@router.post("/", response_model=ScheduledReportResponse, status_code=status.HTTP_201_CREATED)
async def create_scheduled_report(
    sched_in: ScheduledReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = ScheduledReportService(db)
    sched_dict = sched_in.model_dump()
    sched_dict["owner_id"] = current_user.id
    return await service.sched_repo.create(db, obj_in=sched_dict)


@router.post("/process-due", response_model=Dict[str, Any])
async def trigger_due_scheduled_reports(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    service = ScheduledReportService(db)
    count = await service.process_scheduled_reports()
    return {"status": "Success", "processed_count": count}
