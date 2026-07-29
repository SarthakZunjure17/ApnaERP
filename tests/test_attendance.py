import datetime
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.db.session import AsyncSessionLocal
from app.models.attendance import Attendance
from app.models.employee import Employee
from app.models.hr_configuration import HRConfiguration
from app.models.shift import Shift
from app.repositories.attendance import attendance_repository
from app.repositories.department import department_repository
from app.repositories.employee import employee_repository
from app.repositories.hr_configuration import hr_configuration_repository
from app.repositories.shift import shift_repository
from app.repositories.user import user_repository
from app.schemas.attendance import CheckInRequest, CheckOutRequest
from app.services.attendance import AttendanceService
from app.services.attendance_engine import AttendanceEngine
from app.exceptions.base import ApnaERPException


@pytest_asyncio.fixture
async def admin_token(async_client: AsyncClient) -> str:
    """Fixture creating Super Admin user and returning Bearer JWT token."""
    unique_id = uuid.uuid4().hex[:6]
    email = f"attadmin_{unique_id}@example.com"
    username = f"attadmin_{unique_id}"

    reg_payload = {
        "full_name": "Attendance Admin",
        "email": email,
        "username": username,
        "password": "AdminPassword123!",
    }
    reg_resp = await async_client.post("/api/v1/auth/register", json=reg_payload)
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
        dept_id = None
        from app.utils.pagination import PaginationParams
        depts_res = await department_repository.get_multi_paginated(session, params=PaginationParams(page=1, page_size=1))
        if depts_res.items:
            dept_id = depts_res.items[0].id
        else:
            from app.models.department import Department
            code = f"DEPT-{uuid.uuid4().hex[:6]}"
            new_dept = Department(code=code, name=f"Test Dept {code}", is_active=True)
            session.add(new_dept)
            await session.commit()
            await session.refresh(new_dept)
            dept_id = new_dept.id

        unique_code = f"EMP-ATT-{uuid.uuid4().hex[:6]}"
        emp = Employee(
            employee_code=unique_code,
            first_name="Attendance",
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
async def sample_shift():
    """Fixture creating a standard day shift (09:00 to 17:00)."""
    async with AsyncSessionLocal() as session:
        code = f"SHF-DAY-{uuid.uuid4().hex[:6]}"
        shift = Shift(
            code=code,
            name=f"Day Shift {code}",
            start_time=datetime.time(9, 0),
            end_time=datetime.time(17, 0),
            break_duration_minutes=60,
            grace_period_minutes=15,
            minimum_working_hours=4.0,
            maximum_working_hours=10.0,
            is_night_shift=False,
            is_active=True,
        )
        session.add(shift)
        await session.commit()
        await session.refresh(shift)
        return shift


@pytest_asyncio.fixture
async def night_shift():
    """Fixture creating an overnight shift (22:00 to 06:00 next day)."""
    async with AsyncSessionLocal() as session:
        code = f"SHF-NIGHT-{uuid.uuid4().hex[:6]}"
        shift = Shift(
            code=code,
            name=f"Night Shift {code}",
            start_time=datetime.time(22, 0),
            end_time=datetime.time(6, 0),
            break_duration_minutes=30,
            grace_period_minutes=15,
            minimum_working_hours=4.0,
            maximum_working_hours=10.0,
            is_night_shift=True,
            is_active=True,
        )
        session.add(shift)
        await session.commit()
        await session.refresh(shift)
        return shift


# ============================================================================
# 1. DOMAIN SERVICE UNIT TESTS (AttendanceEngine)
# ============================================================================

def test_attendance_engine_present_and_worked_minutes(sample_shift):
    """Tests normal Present status calculation with worked and expected minutes."""
    target_date = datetime.date(2026, 7, 27)  # Monday
    check_in = datetime.datetime.combine(target_date, datetime.time(9, 0), tzinfo=datetime.timezone.utc)
    check_out = datetime.datetime.combine(target_date, datetime.time(17, 0), tzinfo=datetime.timezone.utc)

    result = AttendanceEngine.calculate_attendance(
        attendance_date=target_date,
        check_in_time=check_in,
        check_out_time=check_out,
        break_minutes=60,
        shift=sample_shift,
        is_holiday=False,
    )

    assert result.attendance_status == "Present"
    assert result.worked_minutes == 420  # 8 hours - 1 hr break = 7 hrs = 420 mins
    assert result.expected_minutes == 420
    assert result.late_minutes == 0
    assert result.early_departure_minutes == 0


def test_attendance_engine_late_arrival(sample_shift):
    """Tests Late status calculation when check-in exceeds grace period."""
    target_date = datetime.date(2026, 7, 27)
    # Check-in at 09:30 AM (grace period is 15 mins -> 09:15 AM)
    check_in = datetime.datetime.combine(target_date, datetime.time(9, 30), tzinfo=datetime.timezone.utc)
    check_out = datetime.datetime.combine(target_date, datetime.time(17, 0), tzinfo=datetime.timezone.utc)

    result = AttendanceEngine.calculate_attendance(
        attendance_date=target_date,
        check_in_time=check_in,
        check_out_time=check_out,
        break_minutes=60,
        shift=sample_shift,
        is_holiday=False,
    )

    assert result.attendance_status == "Late"
    assert result.late_minutes == 30


def test_attendance_engine_half_day(sample_shift):
    """Tests Half Day status calculation when worked minutes < minimum working hours (4 hrs = 240 mins)."""
    target_date = datetime.date(2026, 7, 27)
    # Check in 09:00 AM, Check out 12:00 PM (3 hours worked)
    check_in = datetime.datetime.combine(target_date, datetime.time(9, 0), tzinfo=datetime.timezone.utc)
    check_out = datetime.datetime.combine(target_date, datetime.time(12, 0), tzinfo=datetime.timezone.utc)

    result = AttendanceEngine.calculate_attendance(
        attendance_date=target_date,
        check_in_time=check_in,
        check_out_time=check_out,
        break_minutes=0,
        shift=sample_shift,
    )

    assert result.attendance_status == "Half Day"
    assert result.worked_minutes == 180  # 3 hrs = 180 mins < 240 mins


def test_attendance_engine_weekend_and_holiday(sample_shift):
    """Tests Weekend and Holiday status determination."""
    sunday_date = datetime.date(2026, 7, 26)  # Sunday
    hr_config = HRConfiguration(
        organization_name="Test Org",
        organization_code="ORG-TEST",
        timezone="UTC",
        weekend_configuration=["Saturday", "Sunday"],
        standard_working_hours_per_day=8.0,
        grace_period_minutes=15,
        minimum_working_hours=4.0,
        is_active=True,
    )

    # Weekend test
    weekend_res = AttendanceEngine.calculate_attendance(
        attendance_date=sunday_date,
        hr_config=hr_config,
    )
    assert weekend_res.attendance_status == "Weekend"
    assert weekend_res.expected_minutes == 0

    # Holiday test on weekday
    weekday_date = datetime.date(2026, 7, 27)
    holiday_res = AttendanceEngine.calculate_attendance(
        attendance_date=weekday_date,
        hr_config=hr_config,
        is_holiday=True,
    )
    assert holiday_res.attendance_status == "Holiday"
    assert holiday_res.expected_minutes == 0


def test_attendance_engine_overnight_shift(night_shift):
    """Tests overnight shift spanning across midnight (22:00 to 06:00 next day)."""
    start_date = datetime.date(2026, 7, 27)
    next_date = datetime.date(2026, 7, 28)

    check_in = datetime.datetime.combine(start_date, datetime.time(22, 0), tzinfo=datetime.timezone.utc)
    check_out = datetime.datetime.combine(next_date, datetime.time(6, 0), tzinfo=datetime.timezone.utc)

    result = AttendanceEngine.calculate_attendance(
        attendance_date=start_date,
        check_in_time=check_in,
        check_out_time=check_out,
        break_minutes=30,
        shift=night_shift,
    )

    assert result.attendance_status == "Present"
    assert result.worked_minutes == 450  # 8 hrs - 30m break = 7.5 hrs = 450 mins
    assert result.late_minutes == 0
    assert result.early_departure_minutes == 0


# ============================================================================
# 2. REPOSITORY & SERVICE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_attendance_service_checkin_checkout(sample_employee, sample_shift):
    """Tests AttendanceService check-in and check-out workflows."""
    async with AsyncSessionLocal() as session:
        service = AttendanceService(session)

        # Check-in
        check_in_time = datetime.datetime(2026, 7, 27, 9, 0, tzinfo=datetime.timezone.utc)
        checkin_req = CheckInRequest(
            employee_id=sample_employee.id,
            check_in_time=check_in_time,
            shift_id=sample_shift.id,
        )
        att_record = await service.process_check_in(data=checkin_req)
        assert att_record.id is not None
        assert att_record.attendance_status == "Missing Check-out"
        assert att_record.check_in_time == check_in_time

        # Check-out
        check_out_time = datetime.datetime(2026, 7, 27, 17, 0, tzinfo=datetime.timezone.utc)
        checkout_req = CheckOutRequest(
            employee_id=sample_employee.id,
            check_out_time=check_out_time,
            break_minutes=60,
        )
        updated_att = await service.process_check_out(data=checkout_req)
        assert updated_att.attendance_status == "Present"
        assert updated_att.worked_minutes == 420


@pytest.mark.asyncio
async def test_attendance_service_locked_guard(sample_employee, sample_shift):
    """Tests that locked attendance records reject check-out or manual corrections."""
    async with AsyncSessionLocal() as session:
        service = AttendanceService(session)

        # 1. Create and check-in
        check_in_time = datetime.datetime(2026, 7, 27, 9, 0, tzinfo=datetime.timezone.utc)
        att_record = await service.process_check_in(
            data=CheckInRequest(employee_id=sample_employee.id, check_in_time=check_in_time, shift_id=sample_shift.id)
        )

        # 2. Lock the attendance record directly in DB
        db_rec = await attendance_repository.get_by_id(session, att_record.id)
        db_rec.is_locked = True
        await session.commit()

        # 3. Attempt check-out on locked record -> Expect ATTENDANCE_LOCKED
        checkout_req = CheckOutRequest(
            employee_id=sample_employee.id,
            check_out_time=datetime.datetime(2026, 7, 27, 17, 0, tzinfo=datetime.timezone.utc),
        )
        with pytest.raises(ApnaERPException) as exc_info:
            await service.process_check_out(data=checkout_req)
        assert exc_info.value.error_code == "ATTENDANCE_LOCKED"


# ============================================================================
# 3. REST API ENDPOINT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_attendance_api_full_workflow(async_client: AsyncClient, admin_token: str, sample_employee: Employee):
    """Tests REST API endpoints for Check-in, Check-out, Correction, Lock, and Queries."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. POST /api/v1/attendance/checkin
    checkin_payload = {
        "employee_id": str(sample_employee.id),
        "check_in_time": "2026-07-27T09:00:00Z",
    }
    res_in = await async_client.post("/api/v1/attendance/checkin", json=checkin_payload, headers=headers)
    assert res_in.status_code == 200
    att_dict = res_in.json()
    att_id = att_dict["id"]
    assert att_dict["attendance_status"] == "Missing Check-out"

    # 2. GET /api/v1/attendance/{id}
    res_get = await async_client.get(f"/api/v1/attendance/{att_id}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["employee_id"] == str(sample_employee.id)

    # 3. POST /api/v1/attendance/checkout
    checkout_payload = {
        "employee_id": str(sample_employee.id),
        "check_out_time": "2026-07-27T17:00:00Z",
        "break_minutes": 60,
    }
    res_out = await async_client.post("/api/v1/attendance/checkout", json=checkout_payload, headers=headers)
    assert res_out.status_code == 200
    assert res_out.json()["attendance_status"] == "Present"

    # 4. PATCH /api/v1/attendance/correct
    correct_payload = {
        "attendance_id": att_id,
        "correction_notes": "Manual adjustment for doctor appointment",
        "break_minutes": 30,
    }
    res_corr = await async_client.patch("/api/v1/attendance/correct", json=correct_payload, headers=headers)
    assert res_corr.status_code == 200
    assert res_corr.json()["is_manual_correction"] is True
    assert res_corr.json()["correction_notes"] == "Manual adjustment for doctor appointment"

    # 5. PATCH /api/v1/attendance/lock
    lock_payload = {
        "attendance_ids": [att_id],
    }
    res_lock = await async_client.patch("/api/v1/attendance/lock", json=lock_payload, headers=headers)
    assert res_lock.status_code == 200
    assert res_lock.json()[0]["is_locked"] is True

    # 6. GET /api/v1/attendance/employee/{id}?year=2026&month=7
    res_emp_month = await async_client.get(
        f"/api/v1/attendance/employee/{sample_employee.id}?year=2026&month=7", headers=headers
    )
    assert res_emp_month.status_code == 200
    assert len(res_emp_month.json()) >= 1

    # 7. GET /api/v1/attendance/month?start_date=2026-07-01&end_date=2026-07-31
    res_summary = await async_client.get(
        "/api/v1/attendance/month?start_date=2026-07-01&end_date=2026-07-31", headers=headers
    )
    assert res_summary.status_code == 200
    assert res_summary.json()["total_days"] >= 1


@pytest.mark.asyncio
async def test_attendance_api_rbac_unauthorized(async_client: AsyncClient):
    """Tests that unauthenticated requests to Attendance API return 401 Unauthorized."""
    res = await async_client.get("/api/v1/attendance")
    assert res.status_code == 401
