import datetime
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.db.session import AsyncSessionLocal
from app.models.department import Department
from app.models.employee import Employee
from app.models.shift import Shift
from app.repositories.shift import shift_repository
from app.repositories.user import user_repository
from app.schemas.shift import ShiftCreate, ShiftUpdate
from app.services.shift import ShiftService
from app.exceptions.base import ApnaERPException


@pytest_asyncio.fixture
async def admin_token(async_client: AsyncClient) -> str:
    """Fixture creating Super Admin user and returning Bearer JWT token."""
    unique_id = uuid.uuid4().hex[:6]
    email = f"shiftadmin_{unique_id}@example.com"
    username = f"shiftadmin_{unique_id}"

    reg_payload = {
        "full_name": "Shift Admin",
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


@pytest.mark.asyncio
async def test_shift_repository_crud_and_lookups():
    """Tests ShiftRepository CRUD operations and unique lookups."""
    async with AsyncSessionLocal() as session:
        code = f"REPO-{uuid.uuid4().hex[:6]}"
        shift_in = ShiftCreate(
            code=code,
            name=f"Test Repository Shift {code}",
            description="Repository unit test shift",
            start_time=datetime.time(9, 0, 0),
            end_time=datetime.time(17, 0, 0),
            break_duration_minutes=60,
            grace_period_minutes=15,
            minimum_working_hours=4.0,
            maximum_working_hours=12.0,
            is_night_shift=False,
            is_flexible_shift=False,
            is_active=True,
        )
        shift = await shift_repository.create(session, obj_in=shift_in)
        assert shift.id is not None
        assert shift.code == code
        assert shift.duration_hours == 8.0

        # Lookups
        by_code = await shift_repository.get_by_code(session, code.lower())
        assert by_code is not None
        assert by_code.id == shift.id

        by_name = await shift_repository.get_by_name(session, f"Test Repository Shift {code}")
        assert by_name is not None
        assert by_name.id == shift.id

        assert await shift_repository.exists_by_code(session, code) is True
        assert await shift_repository.exists_by_name(session, f"Test Repository Shift {code}") is True


@pytest.mark.asyncio
async def test_shift_service_overnight_and_validations():
    """Tests ShiftService duration calculations, overnight auto-detection, and sanity rules."""
    async with AsyncSessionLocal() as session:
        service = ShiftService(session)

        # 1. Overnight Shift (22:00 to 06:00)
        code = f"NIGHT-{uuid.uuid4().hex[:6]}"
        overnight_data = ShiftCreate(
            code=code,
            name=f"Night Owl Shift {code}",
            description="Overnight shift across midnight",
            start_time=datetime.time(22, 0, 0),
            end_time=datetime.time(6, 0, 0),
            break_duration_minutes=45,
            grace_period_minutes=15,
            minimum_working_hours=4.0,
            maximum_working_hours=10.0,
            is_night_shift=False,  # Should be auto-set to True
            is_flexible_shift=False,
            is_active=True,
        )
        night_shift = await service.create_shift(data=overnight_data)
        assert night_shift.is_night_shift is True
        assert night_shift.duration_hours == 8.0

        # 2. Duplicate Code Error
        with pytest.raises(ApnaERPException) as exc_info:
            await service.create_shift(data=overnight_data)
        assert exc_info.value.error_code == "DUPLICATE_SHIFT_CODE"

        # 3. Invalid Break Duration >= Shift Duration (8 hours)
        bad_break_code = f"BAD-BREAK-{uuid.uuid4().hex[:6]}"
        invalid_break_data = ShiftCreate(
            code=bad_break_code,
            name=f"Bad Break Shift {bad_break_code}",
            start_time=datetime.time(9, 0, 0),
            end_time=datetime.time(17, 0, 0),
            break_duration_minutes=480,  # 8 hours break in 8 hour shift
            grace_period_minutes=15,
            minimum_working_hours=4.0,
            maximum_working_hours=12.0,
            is_night_shift=False,
            is_flexible_shift=False,
            is_active=True,
        )
        with pytest.raises(ApnaERPException) as exc_info:
            await service.create_shift(data=invalid_break_data)
        assert exc_info.value.error_code == "INVALID_BREAK_DURATION"

        # 4. Invalid Working Hours (min > max)
        bad_hours_code = f"BAD-HOURS-{uuid.uuid4().hex[:6]}"
        invalid_hours_data = ShiftCreate(
            code=bad_hours_code,
            name=f"Bad Hours Shift {bad_hours_code}",
            start_time=datetime.time(9, 0, 0),
            end_time=datetime.time(17, 0, 0),
            break_duration_minutes=60,
            grace_period_minutes=15,
            minimum_working_hours=10.0,
            maximum_working_hours=8.0,
            is_night_shift=False,
            is_flexible_shift=False,
            is_active=True,
        )
        with pytest.raises(ApnaERPException) as exc_info:
            await service.create_shift(data=invalid_hours_data)
        assert exc_info.value.error_code == "INVALID_WORKING_HOURS"


@pytest.mark.asyncio
async def test_active_employee_shift_deletion_guard():
    """Tests that soft-deleting a shift assigned to active employees is blocked."""
    async with AsyncSessionLocal() as session:
        service = ShiftService(session)

        code = f"GUARD-{uuid.uuid4().hex[:6]}"
        shift_data = ShiftCreate(
            code=code,
            name=f"Assigned Shift Guard {code}",
            start_time=datetime.time(9, 0, 0),
            end_time=datetime.time(17, 0, 0),
            break_duration_minutes=60,
            grace_period_minutes=15,
            minimum_working_hours=4.0,
            maximum_working_hours=12.0,
            is_night_shift=False,
            is_flexible_shift=False,
            is_active=True,
        )
        shift = await service.create_shift(data=shift_data)

        dept = Department(
            code=f"DEPT-{code}",
            name=f"Guard Dept {code}",
            is_active=True,
        )
        session.add(dept)
        await session.flush()

        emp = Employee(
            employee_code=f"EMP-{code}",
            first_name="Shift",
            last_name="Test",
            work_email=f"shift.{code}@apnaerp.com",
            department_id=dept.id,
            shift_id=shift.id,
            joining_date=datetime.date(2026, 1, 1),
            employment_type="Full Time",
            employment_status="Active",
            is_active=True,
        )
        session.add(emp)
        await session.commit()

        # Attempt deletion
        with pytest.raises(ApnaERPException) as exc_info:
            await service.delete_shift(shift_id=shift.id)
        assert exc_info.value.error_code == "ASSIGNED_EMPLOYEES_EXIST"
        assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_shift_api_endpoints(async_client: AsyncClient, admin_token: str):
    """Tests RESTful API endpoints for Shift Management."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    code = f"API-{uuid.uuid4().hex[:6]}"

    # 1. Create Shift via POST /api/v1/shifts
    payload = {
        "code": code,
        "name": f"API Standard Shift {code}",
        "description": "Created via API test",
        "start_time": "09:00:00",
        "end_time": "17:00:00",
        "break_duration_minutes": 60,
        "grace_period_minutes": 15,
        "minimum_working_hours": 4.0,
        "maximum_working_hours": 12.0,
        "is_night_shift": False,
        "is_flexible_shift": False,
        "is_active": True,
    }
    create_res = await async_client.post(
        "/api/v1/shifts",
        json=payload,
        headers=headers,
    )
    assert create_res.status_code == 201
    shift_dict = create_res.json()
    shift_id = shift_dict["id"]
    assert shift_dict["code"] == code
    assert shift_dict["duration_hours"] == 8.0

    # 2. Get Shift Details via GET /api/v1/shifts/{id}
    get_res = await async_client.get(
        f"/api/v1/shifts/{shift_id}",
        headers=headers,
    )
    assert get_res.status_code == 200
    assert get_res.json()["name"] == f"API Standard Shift {code}"

    # 3. List Shifts via GET /api/v1/shifts
    list_res = await async_client.get(
        "/api/v1/shifts",
        headers=headers,
    )
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1

    # 4. Update Shift via PUT /api/v1/shifts/{id}
    update_res = await async_client.put(
        f"/api/v1/shifts/{shift_id}",
        json={"name": f"API Updated {code}", "grace_period_minutes": 30},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == f"API Updated {code}"
    assert update_res.json()["grace_period_minutes"] == 30

    # 5. Delete Shift via DELETE /api/v1/shifts/{id}
    del_res = await async_client.delete(
        f"/api/v1/shifts/{shift_id}",
        headers=headers,
    )
    assert del_res.status_code == 200
    assert del_res.json()["is_deleted"] is True

    # 6. Restore Shift via PATCH /api/v1/shifts/{id}/restore
    restore_res = await async_client.patch(
        f"/api/v1/shifts/{shift_id}/restore",
        headers=headers,
    )
    assert restore_res.status_code == 200
    assert restore_res.json()["is_deleted"] is False


@pytest.mark.asyncio
async def test_shift_api_rbac_unauthorized(async_client: AsyncClient):
    """Tests that unauthenticated requests to Shift API return 401 Unauthorized."""
    res = await async_client.get("/api/v1/shifts")
    assert res.status_code == 401
