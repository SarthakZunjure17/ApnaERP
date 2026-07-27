import datetime
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select

from unittest.mock import patch

from app.db.session import AsyncSessionLocal


@pytest.fixture(autouse=True)
def mock_celery_task():
    with patch("app.services.shift_assignment.send_shift_assignment_notification_task.delay") as mock_delay:
        yield mock_delay
from app.models.attendance import Attendance
from app.models.department import Department
from app.models.employee import Employee
from app.models.shift import Shift
from app.models.shift_assignment import ShiftAssignment
from app.models.user import User
from app.repositories.department import department_repository
from app.repositories.user import user_repository
from app.schemas.shift_assignment import ShiftAssignmentCreate, ShiftAssignmentUpdate, ShiftAssignmentEndRequest
from app.services.attendance import AttendanceService
from app.services.shift_assignment import ShiftAssignmentService
from app.utils.pagination import PaginationParams


@pytest_asyncio.fixture
async def admin_auth_token(async_client: AsyncClient):
    """Fixture returning JWT auth token for Super Admin."""
    email = f"shiftadmin_{uuid.uuid4().hex[:6]}@example.com"
    reg_resp = await async_client.post("/api/v1/auth/register", json={
        "email": email,
        "username": f"shiftadmin_{uuid.uuid4().hex[:6]}",
        "password": "AdminPassword123!",
        "full_name": "Shift Admin",
    })
    user_id = uuid.UUID(reg_resp.json()["id"])

    async with AsyncSessionLocal() as session:
        user = await user_repository.get_by_id(session, user_id)
        if user:
            user.is_superuser = True
            await session.commit()

    login_resp = await async_client.post("/api/v1/auth/login", json={
        "username_or_email": email,
        "password": "AdminPassword123!",
    })
    return login_resp.json()["access_token"]


@pytest_asyncio.fixture
async def sample_employee():
    """Fixture creating a test active Employee."""
    async with AsyncSessionLocal() as session:
        depts_res = await department_repository.get_multi_paginated(session, params=PaginationParams(page=1, page_size=1))
        if depts_res.items:
            dept_id = depts_res.items[0].id
        else:
            code = f"DEPT-{uuid.uuid4().hex[:6]}"
            new_dept = Department(code=code, name=f"Test Dept {code}", is_active=True)
            session.add(new_dept)
            await session.commit()
            await session.refresh(new_dept)
            dept_id = new_dept.id

        unique_code = f"EMP-SA-{uuid.uuid4().hex[:6]}"
        emp = Employee(
            employee_code=unique_code,
            first_name="ShiftAssign",
            last_name="Tester",
            work_email=f"{unique_code.lower()}@example.com",
            joining_date=datetime.date(2025, 1, 1),
            department_id=dept_id,
            is_active=True,
        )
        session.add(emp)
        await session.commit()
        await session.refresh(emp)
        return emp


@pytest_asyncio.fixture
async def sample_shifts():
    """Fixture creating Day Shift and Night Shift."""
    async with AsyncSessionLocal() as session:
        code1 = f"SHIFT-DAY-{uuid.uuid4().hex[:4]}"
        day_shift = Shift(
            name=f"Day Shift {uuid.uuid4().hex[:4]}",
            code=code1,
            start_time=datetime.time(9, 0),
            end_time=datetime.time(17, 0),
            is_night_shift=False,
            minimum_working_hours=4.0,
            grace_period_minutes=15,
            is_active=True,
        )

        code2 = f"SHIFT-NIGHT-{uuid.uuid4().hex[:4]}"
        night_shift = Shift(
            name=f"Night Shift {uuid.uuid4().hex[:4]}",
            code=code2,
            start_time=datetime.time(22, 0),
            end_time=datetime.time(6, 0),
            is_night_shift=True,
            minimum_working_hours=4.0,
            grace_period_minutes=15,
            is_active=True,
        )

        session.add(day_shift)
        session.add(night_shift)
        await session.commit()
        await session.refresh(day_shift)
        await session.refresh(night_shift)
        return day_shift, night_shift


@pytest.mark.asyncio
async def test_shift_assignment_create_and_resolve(sample_employee, sample_shifts):
    """Tests creating shift assignment and resolving shift by date."""
    day_shift, night_shift = sample_shifts
    async with AsyncSessionLocal() as session:
        service = ShiftAssignmentService(session)

        # Assign Day Shift for 2026-07-01 to 2026-07-15
        create_data = ShiftAssignmentCreate(
            employee_id=sample_employee.id,
            shift_id=day_shift.id,
            effective_from=datetime.date(2026, 7, 1),
            effective_to=datetime.date(2026, 7, 15),
            assignment_type="Permanent",
            reason="Initial schedule assignment",
        )
        assignment = await service.assign_shift(create_data)
        assert assignment.id is not None

        # Resolve on 2026-07-10 (within range) -> Day Shift
        resolved_10 = await service.resolve_shift_for_date(sample_employee.id, datetime.date(2026, 7, 10))
        assert resolved_10 is not None
        assert resolved_10.id == day_shift.id

        # Resolve on 2026-07-20 (outside range) -> None
        resolved_20 = await service.resolve_shift_for_date(sample_employee.id, datetime.date(2026, 7, 20))
        assert resolved_20 is None


@pytest.mark.asyncio
async def test_shift_assignment_overlap_rejection(sample_employee, sample_shifts):
    """Tests date range overlap prevention for the same employee."""
    day_shift, night_shift = sample_shifts
    async with AsyncSessionLocal() as session:
        service = ShiftAssignmentService(session)

        # 1st assignment: 2026-08-01 to 2026-08-15
        await service.assign_shift(
            ShiftAssignmentCreate(
                employee_id=sample_employee.id,
                shift_id=day_shift.id,
                effective_from=datetime.date(2026, 8, 1),
                effective_to=datetime.date(2026, 8, 15),
            )
        )

        # Overlapping assignment: 2026-08-10 to 2026-08-25 -> Should fail
        from app.exceptions.base import ApnaERPException
        with pytest.raises(ApnaERPException) as exc_info:
            await service.assign_shift(
                ShiftAssignmentCreate(
                    employee_id=sample_employee.id,
                    shift_id=night_shift.id,
                    effective_from=datetime.date(2026, 8, 10),
                    effective_to=datetime.date(2026, 8, 25),
                )
            )
        assert exc_info.value.error_code == "OVERLAPPING_SHIFT_ASSIGNMENT"


@pytest.mark.asyncio
async def test_shift_assignment_end_and_update(sample_employee, sample_shifts):
    """Tests updating date range and ending an assignment."""
    day_shift, night_shift = sample_shifts
    async with AsyncSessionLocal() as session:
        service = ShiftAssignmentService(session)

        assignment = await service.assign_shift(
            ShiftAssignmentCreate(
                employee_id=sample_employee.id,
                shift_id=day_shift.id,
                effective_from=datetime.date(2026, 9, 1),
                effective_to=None,  # Open-ended
            )
        )

        # End assignment on 2026-09-30
        ended = await service.end_assignment(
            id=assignment.id,
            data=ShiftAssignmentEndRequest(end_date=datetime.date(2026, 9, 30)),
        )
        assert ended.effective_to == datetime.date(2026, 9, 30)


@pytest.mark.asyncio
async def test_shift_assignment_locked_attendance_guard(sample_employee, sample_shifts):
    """Tests protection against modifying shift assignments during locked attendance periods."""
    day_shift, night_shift = sample_shifts
    async with AsyncSessionLocal() as session:
        service = ShiftAssignmentService(session)

        assignment = await service.assign_shift(
            ShiftAssignmentCreate(
                employee_id=sample_employee.id,
                shift_id=day_shift.id,
                effective_from=datetime.date(2026, 10, 1),
                effective_to=datetime.date(2026, 10, 31),
            )
        )

        # Create locked Attendance record on 2026-10-15
        att = Attendance(
            employee_id=sample_employee.id,
            attendance_date=datetime.date(2026, 10, 15),
            shift_id=day_shift.id,
            attendance_status="Present",
            is_locked=True,
        )
        session.add(att)
        await session.commit()

        # Deleting assignment should fail with ATTENDANCE_LOCKED
        from app.exceptions.base import ApnaERPException
        with pytest.raises(ApnaERPException) as exc_info:
            await service.delete_assignment(assignment.id)
        assert exc_info.value.error_code == "ATTENDANCE_LOCKED"


@pytest.mark.asyncio
async def test_attendance_integration_historical_resolution(sample_employee, sample_shifts):
    """Tests Attendance Engine dynamically resolving different shifts based on assignment dates."""
    day_shift, night_shift = sample_shifts
    async with AsyncSessionLocal() as session:
        sa_service = ShiftAssignmentService(session)
        att_service = AttendanceService(session)

        # Assignment 1: Day Shift from 2026-11-01 to 2026-11-15
        await sa_service.assign_shift(
            ShiftAssignmentCreate(
                employee_id=sample_employee.id,
                shift_id=day_shift.id,
                effective_from=datetime.date(2026, 11, 1),
                effective_to=datetime.date(2026, 11, 15),
            )
        )

        # Assignment 2: Night Shift from 2026-11-16 to 2026-11-30
        await sa_service.assign_shift(
            ShiftAssignmentCreate(
                employee_id=sample_employee.id,
                shift_id=night_shift.id,
                effective_from=datetime.date(2026, 11, 16),
                effective_to=datetime.date(2026, 11, 30),
            )
        )

        # Check-in on 2026-11-05 (Day Shift range)
        dt_day = datetime.datetime(2026, 11, 5, 9, 0, tzinfo=datetime.timezone.utc)
        from app.schemas.attendance import CheckInRequest
        att_day = await att_service.process_check_in(CheckInRequest(employee_id=sample_employee.id, check_in_time=dt_day))
        assert att_day.shift_id == day_shift.id

        # Check-in on 2026-11-20 (Night Shift range)
        dt_night = datetime.datetime(2026, 11, 20, 22, 0, tzinfo=datetime.timezone.utc)
        att_night = await att_service.process_check_in(CheckInRequest(employee_id=sample_employee.id, check_in_time=dt_night))
        assert att_night.shift_id == night_shift.id


@pytest.mark.asyncio
async def test_shift_assignment_api_full_workflow(async_client: AsyncClient, admin_auth_token: str, sample_employee, sample_shifts):
    """Tests REST API endpoints for Shift Assignment management."""
    headers = {"Authorization": f"Bearer {admin_auth_token}"}
    day_shift, night_shift = sample_shifts

    # 1. Create Shift Assignment
    payload = {
        "employee_id": str(sample_employee.id),
        "shift_id": str(day_shift.id),
        "effective_from": "2026-12-01",
        "effective_to": "2026-12-31",
        "assignment_type": "Permanent",
        "reason": "REST API Test Assignment",
    }
    create_resp = await async_client.post("/api/v1/shift-assignments", json=payload, headers=headers)
    assert create_resp.status_code == 201
    assign_data = create_resp.json()
    assign_id = assign_data["id"]

    # 2. Get Shift Assignment by ID
    get_resp = await async_client.get(f"/api/v1/shift-assignments/{assign_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == assign_id

    # 3. List Employee Assignments
    emp_list_resp = await async_client.get(f"/api/v1/shift-assignments/employees/{sample_employee.id}/shift-assignments", headers=headers)
    assert emp_list_resp.status_code == 200
    assert emp_list_resp.json()["total"] >= 1

    # 4. List All Shift Assignments
    all_resp = await async_client.get("/api/v1/shift-assignments", headers=headers)
    assert all_resp.status_code == 200
    assert all_resp.json()["total"] >= 1

    # 5. Update Shift Assignment
    update_resp = await async_client.put(
        f"/api/v1/shift-assignments/{assign_id}",
        json={"shift_id": str(night_shift.id), "reason": "Switched to night shift"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["shift_id"] == str(night_shift.id)

    # 6. End Shift Assignment
    end_resp = await async_client.patch(
        f"/api/v1/shift-assignments/{assign_id}/end",
        json={"end_date": "2026-12-25"},
        headers=headers,
    )
    assert end_resp.status_code == 200
    assert end_resp.json()["effective_to"] == "2026-12-25"

    # 7. Delete Shift Assignment
    del_resp = await async_client.delete(f"/api/v1/shift-assignments/{assign_id}", headers=headers)
    assert del_resp.status_code == 204
