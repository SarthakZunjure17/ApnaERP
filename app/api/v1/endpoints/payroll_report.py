from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, has_permission
from app.exceptions.base import NotFoundException
from app.models.user import User
from app.schemas.payroll_finalization import (
    PayrollReportGenerateRequest,
    PayrollReportSnapshotResponse,
)
from app.services.file import file_service
from app.services.payroll_finalization_services import PayrollReportService
from app.utils.pagination import PaginatedResult, PaginationParams

router = APIRouter(prefix="/payroll-reports", tags=["Payroll Reports"])


@router.get("", response_model=PaginatedResult[PayrollReportSnapshotResponse])
async def get_payroll_reports(
    payroll_period_id: Optional[uuid.UUID] = Query(None),
    report_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("payroll.report.generate")),
):
    service = PayrollReportService(db)
    return await service.snapshot_repo.get_filtered_snapshots(
        db,
        params=PaginationParams(page=page, page_size=page_size),
        payroll_period_id=payroll_period_id,
        report_type=report_type,
    )


@router.post("/generate", response_model=PayrollReportSnapshotResponse, status_code=status.HTTP_201_CREATED)
async def generate_payroll_report(
    request: PayrollReportGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("payroll.report.generate")),
):
    service = PayrollReportService(db)
    return await service.generate_report(request, current_user=current_user)


@router.get("/{report_id}/download")
async def download_payroll_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_permission("payroll.report.generate")),
):
    service = PayrollReportService(db)
    snapshot = await service.snapshot_repo.get_by_id(db, report_id)
    if not snapshot or not snapshot.file_id:
        raise NotFoundException(message=f"PayrollReportSnapshot {report_id} not found.")

    file_obj, file_bytes = await file_service.get_file_for_download(db, file_id=snapshot.file_id, current_user=current_user)
    return Response(
        content=file_bytes,
        media_type=file_obj.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{file_obj.original_filename}"'},
    )
