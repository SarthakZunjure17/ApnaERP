import datetime
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, has_permission
from app.models.user import User
from app.schemas.attendance import (
    AttendanceCorrectionRequest,
    AttendanceListResponse,
    AttendanceLockRequest,
    AttendanceResponse,
    AttendanceSummary,
    CheckInRequest,
    CheckOutRequest,
)
from app.services.attendance import AttendanceService

router = APIRouter()


@router.get(
    "",
    response_model=AttendanceListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Attendance Records",
    description="Retrieves a paginated list of employee attendance records with multi-field filtering and search.",
    dependencies=[Depends(has_permission("attendance.read"))]
)
async def get_attendances(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by status or correction notes"),
    employee_id: Optional[uuid.UUID] = Query(None, description="Filter by employee UUID"),
    department_id: Optional[uuid.UUID] = Query(None, description="Filter by department UUID"),
    start_date: Optional[datetime.date] = Query(None, description="Filter start date"),
    end_date: Optional[datetime.date] = Query(None, description="Filter end date"),
    attendance_status: Optional[str] = Query(None, description="Filter by attendance status"),
    is_locked: Optional[bool] = Query(None, description="Filter by locked status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttendanceListResponse:
    """Gets paginated attendance records."""
    service = AttendanceService(db)
    result = await service.get_attendances(
        page=page,
        page_size=page_size,
        search=search,
        employee_id=employee_id,
        department_id=department_id,
        start_date=start_date,
        end_date=end_date,
        attendance_status=attendance_status,
        is_locked=is_locked,
    )
    return AttendanceListResponse(
        items=[AttendanceResponse.model_validate(rec) for rec in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@router.get(
    "/month",
    response_model=AttendanceSummary,
    status_code=status.HTTP_200_OK,
    summary="Get Monthly Attendance Summary",
    description="Retrieves aggregated summary statistics for a given date range.",
    dependencies=[Depends(has_permission("attendance.read"))]
)
async def get_monthly_attendance_summary(
    start_date: datetime.date = Query(..., description="Range start date"),
    end_date: datetime.date = Query(..., description="Range end date"),
    department_id: Optional[uuid.UUID] = Query(None, description="Optional department filter"),
    employee_id: Optional[uuid.UUID] = Query(None, description="Optional employee filter"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttendanceSummary:
    """Gets attendance summary statistics."""
    service = AttendanceService(db)
    return await service.get_summary(
        start_date=start_date, end_date=end_date, department_id=department_id, employee_id=employee_id
    )


@router.get(
    "/employee/{id}",
    response_model=List[AttendanceResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Employee Monthly Attendance",
    description="Retrieves all attendance records for a specific employee within a given year and month.",
    dependencies=[Depends(has_permission("attendance.read"))]
)
async def get_employee_monthly_attendance(
    id: uuid.UUID,
    year: int = Query(..., ge=1900, le=2100, description="Target calendar year"),
    month: int = Query(..., ge=1, le=12, description="Target calendar month"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[AttendanceResponse]:
    """Gets monthly attendance for an employee."""
    service = AttendanceService(db)
    records = await service.get_employee_monthly_attendance(employee_id=id, year=year, month=month)
    return [AttendanceResponse.model_validate(r) for r in records]


@router.get(
    "/{id}",
    response_model=AttendanceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Attendance Record Details",
    description="Retrieves specific attendance record details by UUID.",
    dependencies=[Depends(has_permission("attendance.read"))]
)
async def get_attendance_by_id(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttendanceResponse:
    """Gets attendance details by ID."""
    service = AttendanceService(db)
    attendance = await service.get_attendance_by_id(attendance_id=id)
    return AttendanceResponse.model_validate(attendance)


@router.post(
    "/checkin",
    response_model=AttendanceResponse,
    status_code=status.HTTP_200_OK,
    summary="Record Check-in",
    description="Records employee check-in timestamp and calculates real-time attendance status and tardiness.",
    dependencies=[Depends(has_permission("attendance.checkin"))]
)
async def process_check_in(
    data: CheckInRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttendanceResponse:
    """Processes check-in."""
    service = AttendanceService(db)
    attendance = await service.process_check_in(data=data, current_user=current_user, request=request)
    return AttendanceResponse.model_validate(attendance)


@router.post(
    "/checkout",
    response_model=AttendanceResponse,
    status_code=status.HTTP_200_OK,
    summary="Record Check-out",
    description="Records employee check-out timestamp and calculates total worked minutes, early departures, and final status.",
    dependencies=[Depends(has_permission("attendance.checkout"))]
)
async def process_check_out(
    data: CheckOutRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttendanceResponse:
    """Processes check-out."""
    service = AttendanceService(db)
    attendance = await service.process_check_out(data=data, current_user=current_user, request=request)
    return AttendanceResponse.model_validate(attendance)


@router.patch(
    "/correct",
    response_model=AttendanceResponse,
    status_code=status.HTTP_200_OK,
    summary="Manually Correct Attendance",
    description="Manually updates an unlocked attendance record with required audit notes.",
    dependencies=[Depends(has_permission("attendance.correct"))]
)
async def correct_attendance(
    data: AttendanceCorrectionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttendanceResponse:
    """Manually corrects attendance."""
    service = AttendanceService(db)
    attendance = await service.correct_attendance(data=data, current_user=current_user, request=request)
    return AttendanceResponse.model_validate(attendance)


@router.patch(
    "/lock",
    response_model=List[AttendanceResponse],
    status_code=status.HTTP_200_OK,
    summary="Lock Attendance Records",
    description="Locks specified attendance records or a date range to prevent further modifications during payroll processing.",
    dependencies=[Depends(has_permission("attendance.lock"))]
)
async def lock_attendance(
    data: AttendanceLockRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[AttendanceResponse]:
    """Locks attendance records."""
    service = AttendanceService(db)
    locked_records = await service.lock_attendance(data=data, current_user=current_user, request=request)
    return [AttendanceResponse.model_validate(r) for r in locked_records]
