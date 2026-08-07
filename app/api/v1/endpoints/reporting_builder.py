from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.reporting import SavedReportCreate, SavedReportResponse
from app.services.reporting_services import ReportBuilderService

router = APIRouter()


@router.get("/generate", response_model=Dict[str, Any])
async def generate_report_data(
    datasource_key: str = Query(..., description="Query identifier (e.g. hr_employees, sales_orders)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    service = ReportBuilderService(db)
    return await service.generate_dynamic_report(datasource_key=datasource_key)


@router.post("/saved", response_model=SavedReportResponse, status_code=status.HTTP_201_CREATED)
async def save_custom_report(
    report_in: SavedReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    service = ReportBuilderService(db)
    return await service.save_custom_report(report_in.model_dump(), user=current_user)


@router.get("/saved", response_model=List[SavedReportResponse])
async def list_user_saved_reports(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Any]:
    service = ReportBuilderService(db)
    return await service.saved_repo.get_user_saved_reports(db, owner_id=current_user.id)
