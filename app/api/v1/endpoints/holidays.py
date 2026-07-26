import datetime
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, has_permission
from app.models.user import User
from app.schemas.holiday import (
    HolidayCreate,
    HolidayListResponse,
    HolidayResponse,
    HolidayUpdate,
)
from app.services.holiday import HolidayService

router = APIRouter()


@router.get(
    "",
    response_model=HolidayListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Holidays",
    description="Retrieves a paginated list of enterprise holiday calendar entries with search and filtering.",
    dependencies=[Depends(has_permission("holiday.read"))]
)
async def get_holidays(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by code, name, description, country, or region"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    holiday_type: Optional[str] = Query(None, description="Filter by holiday type (National, Regional, Company, Optional)"),
    country: Optional[str] = Query(None, description="Filter by target country"),
    state_region: Optional[str] = Query(None, description="Filter by state or region"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HolidayListResponse:
    """Gets paginated holidays."""
    service = HolidayService(db)
    result = await service.get_holidays(
        page=page,
        page_size=page_size,
        search=search,
        is_active=is_active,
        holiday_type=holiday_type,
        country=country,
        state_region=state_region,
    )
    return HolidayListResponse(
        items=[HolidayResponse.model_validate(h) for h in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@router.get(
    "/year/{year}",
    response_model=List[HolidayResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Holidays by Year",
    description="Retrieves active holidays occurring in a specific calendar year (including annual recurring ones).",
    dependencies=[Depends(has_permission("holiday.read"))]
)
async def get_holidays_by_year(
    year: int,
    country: Optional[str] = Query(None, description="Filter by country"),
    state_region: Optional[str] = Query(None, description="Filter by state or region"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[HolidayResponse]:
    """Gets holidays for a specific year."""
    service = HolidayService(db)
    holidays = await service.get_holidays_by_year(year=year, country=country, state_region=state_region)
    return [HolidayResponse.model_validate(h) for h in holidays]


@router.get(
    "/date/{date}",
    response_model=List[HolidayResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Holidays by Date",
    description="Retrieves active holidays falling on a specific date (including annual recurring ones).",
    dependencies=[Depends(has_permission("holiday.read"))]
)
async def get_holidays_by_date(
    date: datetime.date,
    country: Optional[str] = Query(None, description="Filter by country"),
    state_region: Optional[str] = Query(None, description="Filter by state or region"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[HolidayResponse]:
    """Gets holidays falling on a specific date."""
    service = HolidayService(db)
    holidays = await service.get_holidays_by_date(target_date=date, country=country, state_region=state_region)
    return [HolidayResponse.model_validate(h) for h in holidays]


@router.get(
    "/{id}",
    response_model=HolidayResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Holiday Details",
    description="Retrieves specific holiday entry details by UUID.",
    dependencies=[Depends(has_permission("holiday.read"))]
)
async def get_holiday_by_id(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HolidayResponse:
    """Gets holiday details by ID."""
    service = HolidayService(db)
    holiday = await service.get_holiday_by_id(holiday_id=id)
    return HolidayResponse.model_validate(holiday)


@router.post(
    "",
    response_model=HolidayResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Holiday Entry",
    description="Defines a new official holiday entry in the calendar.",
    dependencies=[Depends(has_permission("holiday.create"))]
)
async def create_holiday(
    data: HolidayCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HolidayResponse:
    """Creates a new holiday."""
    service = HolidayService(db)
    holiday = await service.create_holiday(data=data, current_user=current_user, request=request)
    return HolidayResponse.model_validate(holiday)


@router.put(
    "/{id}",
    response_model=HolidayResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Holiday Entry",
    description="Updates existing holiday calendar parameters.",
    dependencies=[Depends(has_permission("holiday.update"))]
)
async def update_holiday(
    id: uuid.UUID,
    data: HolidayUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HolidayResponse:
    """Updates an existing holiday."""
    service = HolidayService(db)
    holiday = await service.update_holiday(holiday_id=id, data=data, current_user=current_user, request=request)
    return HolidayResponse.model_validate(holiday)


@router.delete(
    "/{id}",
    response_model=HolidayResponse,
    status_code=status.HTTP_200_OK,
    summary="Soft Delete Holiday Entry",
    description="Soft deletes a holiday calendar entry.",
    dependencies=[Depends(has_permission("holiday.delete"))]
)
async def delete_holiday(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HolidayResponse:
    """Soft deletes a holiday."""
    service = HolidayService(db)
    holiday = await service.delete_holiday(holiday_id=id, current_user=current_user, request=request)
    return HolidayResponse.model_validate(holiday)


@router.patch(
    "/{id}/restore",
    response_model=HolidayResponse,
    status_code=status.HTTP_200_OK,
    summary="Restore Holiday Entry",
    description="Restores a soft-deleted holiday calendar entry.",
    dependencies=[Depends(has_permission("holiday.restore"))]
)
async def restore_holiday(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HolidayResponse:
    """Restores a soft-deleted holiday."""
    service = HolidayService(db)
    holiday = await service.restore_holiday(holiday_id=id, current_user=current_user, request=request)
    return HolidayResponse.model_validate(holiday)
