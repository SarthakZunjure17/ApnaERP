from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.reporting import ExportReportRequest, ExportReportResult
from app.services.reporting_services import ExportService

router = APIRouter()


@router.post("/", response_model=ExportReportResult)
async def export_report(
    req: ExportReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = ExportService(db)
    return await service.export_report(req, user=current_user)
