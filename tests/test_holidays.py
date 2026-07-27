import datetime
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.db.session import AsyncSessionLocal
from app.models.holiday import Holiday
from app.repositories.holiday import holiday_repository
from app.repositories.user import user_repository
from app.schemas.holiday import HolidayCreate, HolidayType, HolidayUpdate
from app.services.holiday import HolidayService
from app.exceptions.base import ApnaERPException


@pytest_asyncio.fixture
async def admin_token(async_client: AsyncClient) -> str:
    """Fixture creating Super Admin user and returning Bearer JWT token."""
    unique_id = uuid.uuid4().hex[:6]
    email = f"holadmin_{unique_id}@example.com"
    username = f"holadmin_{unique_id}"

    reg_payload = {
        "full_name": "Holiday Admin",
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
async def test_holiday_repository_crud_and_lookups():
    """Tests HolidayRepository CRUD operations and unique lookups."""
    async with AsyncSessionLocal() as session:
        code = f"HOL-REPO-{uuid.uuid4().hex[:6]}"
        country = f"Country-{uuid.uuid4().hex[:4]}"
        holiday_in = HolidayCreate(
            code=code,
            name=f"Test Repo Holiday {code}",
            description="Repository unit test holiday",
            holiday_date=datetime.date(2026, 8, 15),
            holiday_type=HolidayType.NATIONAL,
            country=country,
            state_region=None,
            is_half_day=False,
            is_recurring_annually=True,
            is_active=True,
        )
        holiday = await holiday_repository.create(session, obj_in=holiday_in)
        assert holiday.id is not None
        assert holiday.code == code

        # Lookups
        by_code = await holiday_repository.get_by_code(session, code)
        assert by_code is not None
        assert by_code.id == holiday.id

        assert await holiday_repository.exists_by_code(session, code) is True

        by_date_region = await holiday_repository.get_by_date_and_region(
            session, holiday_date=datetime.date(2026, 8, 15), country=country, state_region=None
        )
        assert by_date_region is not None
        assert by_date_region.id == holiday.id


@pytest.mark.asyncio
async def test_holiday_service_validations_and_recurring():
    """Tests HolidayService duplicate checks and annual recurring projections."""
    async with AsyncSessionLocal() as session:
        service = HolidayService(session)

        code = f"HOL-REC-{uuid.uuid4().hex[:6]}"
        country = f"Country-{uuid.uuid4().hex[:4]}"
        rec_data = HolidayCreate(
            code=code,
            name=f"Annual Independence Day {code}",
            holiday_date=datetime.date(2020, 8, 15),
            holiday_type=HolidayType.NATIONAL,
            country=country,
            is_recurring_annually=True,
            is_active=True,
        )
        rec_holiday = await service.create_holiday(data=rec_data)
        assert rec_holiday.is_recurring_annually is True

        # Query holidays for Year 2026 (should project Aug 15, 2020 -> Aug 15, 2026)
        year_holidays = await service.get_holidays_by_year(year=2026, country=country)
        matching = [h for h in year_holidays if h.code == code]
        assert len(matching) == 1
        assert matching[0].holiday_date == datetime.date(2026, 8, 15)

        # Query holidays by specific date (Aug 15, 2027)
        date_holidays = await service.get_holidays_by_date(
            target_date=datetime.date(2027, 8, 15), country=country
        )
        matching_date = [h for h in date_holidays if h.code == code]
        assert len(matching_date) == 1

        # Duplicate Code Error
        with pytest.raises(ApnaERPException) as exc_info:
            await service.create_holiday(data=rec_data)
        assert exc_info.value.error_code == "DUPLICATE_HOLIDAY_CODE"

        # Duplicate Date + Region Error
        dup_date_data = HolidayCreate(
            code=f"HOL-DUP-{uuid.uuid4().hex[:6]}",
            name="Duplicate Date Holiday",
            holiday_date=datetime.date(2020, 8, 15),
            country=country,
            state_region=None,
        )
        with pytest.raises(ApnaERPException) as exc_info:
            await service.create_holiday(data=dup_date_data)
        assert exc_info.value.error_code == "DUPLICATE_HOLIDAY"


@pytest.mark.asyncio
async def test_holiday_api_endpoints(async_client: AsyncClient, admin_token: str):
    """Tests RESTful API endpoints for Holiday Calendar Management."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    code = f"HOL-API-{uuid.uuid4().hex[:6]}"
    country = f"Country-{uuid.uuid4().hex[:4]}"

    # 1. Create Holiday via POST /api/v1/holidays
    payload = {
        "code": code,
        "name": f"API New Year Holiday {code}",
        "description": "Created via API test",
        "holiday_date": "2026-03-15",
        "holiday_type": "National",
        "country": country,
        "state_region": None,
        "is_half_day": False,
        "is_recurring_annually": True,
        "is_active": True,
    }
    create_res = await async_client.post(
        "/api/v1/holidays",
        json=payload,
        headers=headers,
    )
    assert create_res.status_code == 201
    hol_dict = create_res.json()
    holiday_id = hol_dict["id"]
    assert hol_dict["code"] == code

    # 2. Get Holiday Details via GET /api/v1/holidays/{id}
    get_res = await async_client.get(
        f"/api/v1/holidays/{holiday_id}",
        headers=headers,
    )
    assert get_res.status_code == 200
    assert get_res.json()["name"] == f"API New Year Holiday {code}"

    # 3. Get Holidays by Year via GET /api/v1/holidays/year/2026
    year_res = await async_client.get(
        f"/api/v1/holidays/year/2026?country={country}",
        headers=headers,
    )
    assert year_res.status_code == 200
    year_items = year_res.json()
    assert any(h["code"] == code for h in year_items)

    # 4. Get Holidays by Date via GET /api/v1/holidays/date/2026-03-15
    date_res = await async_client.get(
        f"/api/v1/holidays/date/2026-03-15?country={country}",
        headers=headers,
    )
    assert date_res.status_code == 200
    date_items = date_res.json()
    assert any(h["code"] == code for h in date_items)

    # 5. List Holidays via GET /api/v1/holidays
    list_res = await async_client.get(
        "/api/v1/holidays",
        headers=headers,
    )
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1

    # 6. Update Holiday via PUT /api/v1/holidays/{id}
    update_res = await async_client.put(
        f"/api/v1/holidays/{holiday_id}",
        json={"name": f"API Updated Holiday {code}", "is_half_day": True},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == f"API Updated Holiday {code}"
    assert update_res.json()["is_half_day"] is True

    # 7. Delete Holiday via DELETE /api/v1/holidays/{id}
    del_res = await async_client.delete(
        f"/api/v1/holidays/{holiday_id}",
        headers=headers,
    )
    assert del_res.status_code == 200
    assert del_res.json()["is_deleted"] is True

    # 8. Restore Holiday via PATCH /api/v1/holidays/{id}/restore
    restore_res = await async_client.patch(
        f"/api/v1/holidays/{holiday_id}/restore",
        headers=headers,
    )
    assert restore_res.status_code == 200
    assert restore_res.json()["is_deleted"] is False


@pytest.mark.asyncio
async def test_holiday_api_rbac_unauthorized(async_client: AsyncClient):
    """Tests that unauthenticated requests to Holiday API return 401 Unauthorized."""
    res = await async_client.get("/api/v1/holidays")
    assert res.status_code == 401
