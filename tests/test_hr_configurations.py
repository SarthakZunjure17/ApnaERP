import datetime
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.core.celery import celery_app
from app.db.session import AsyncSessionLocal
from app.models.hr_configuration import HRConfiguration
from app.repositories.hr_configuration import hr_configuration_repository
from app.repositories.user import user_repository
from app.schemas.hr_configuration import HRConfigurationCreate, HRConfigurationUpdate, PayrollCycle
from app.services.hr_configuration import HRConfigurationService


@pytest_asyncio.fixture
async def admin_token(async_client: AsyncClient) -> str:
    """Fixture creating Super Admin user and returning Bearer JWT token."""
    unique_id = uuid.uuid4().hex[:6]
    email = f"cfgadmin_{unique_id}@example.com"
    username = f"cfgadmin_{unique_id}"

    reg_payload = {
        "full_name": "Config Admin",
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
async def test_hr_config_repository_crud():
    """Tests HRConfigurationRepository direct database operations."""
    async with AsyncSessionLocal() as session:
        repo = hr_configuration_repository
        org_code = f"ORG-REPO-{uuid.uuid4().hex[:6]}"

        config = await repo.create(session, obj_in={
            "organization_name": "Repo Enterprise",
            "organization_code": org_code,
            "timezone": "Asia/Kolkata",
            "country": "India",
            "currency": "INR",
            "standard_working_hours_per_day": 8.0,
            "standard_working_days_per_week": 5,
            "weekend_configuration": ["Saturday", "Sunday"],
            "payroll_cycle": "Monthly",
            "is_active": True,
        })
        assert config.id is not None
        assert config.organization_code == org_code
        assert config.is_active is True

        active_config = await repo.get_active_configuration(session, organization_code=org_code)
        assert active_config is not None
        assert active_config.id == config.id

        await repo.deactivate_all_active_configurations(session, organization_code=org_code)
        deactivated = await repo.get_active_configuration(session, organization_code=org_code)
        assert deactivated is None

        await repo.soft_delete(session, id=config.id)
        fetched_del = await repo.get_by_id(session, config.id)
        assert fetched_del is None

        await repo.restore(session, id=config.id)
        fetched_res = await repo.get_by_id(session, config.id)
        assert fetched_res is not None


@pytest.mark.asyncio
async def test_hr_config_service_validations():
    """
    Tests HRConfigurationService domain business rule validations:
    - Invalid IANA timezone
    - Invalid weekend day name
    - Minimum working hours exceeding standard daily hours
    - Invalid currency ISO code
    - Active configuration soft-delete prevention
    """
    async with AsyncSessionLocal() as session:
        service = HRConfigurationService(session)
        org_code = f"ORG-VAL-{uuid.uuid4().hex[:6]}"

        # 1. Invalid Timezone
        with pytest.raises(Exception) as exc_info:
            await service.create_configuration(HRConfigurationCreate(
                organization_name="Val Org",
                organization_code=org_code,
                timezone="Invalid/NonExistent_Zone",
            ))
        assert "INVALID_TIMEZONE" in str(exc_info.value) or "timezone" in str(exc_info.value)

        # 2. Invalid Weekend Day Name
        with pytest.raises(Exception) as exc_info:
            await service.create_configuration(HRConfigurationCreate(
                organization_name="Val Org",
                organization_code=org_code,
                weekend_configuration=["Funday", "Sunday"],
            ))
        assert "INVALID_WEEKEND_CONFIG" in str(exc_info.value) or "weekend" in str(exc_info.value)

        # 3. Minimum Working Hours Exceeding Standard Working Hours
        with pytest.raises(Exception) as exc_info:
            await service.create_configuration(HRConfigurationCreate(
                organization_name="Val Org",
                organization_code=org_code,
                standard_working_hours_per_day=7.0,
                minimum_working_hours=9.0,
            ))
        assert "INVALID_WORKING_HOURS" in str(exc_info.value) or "exceed" in str(exc_info.value)

        # 4. Invalid Currency Code
        with pytest.raises(Exception) as exc_info:
            await service.create_configuration(HRConfigurationCreate(
                organization_name="Val Org",
                organization_code=org_code,
                currency="RUPEES",
            ))
        assert "INVALID_CURRENCY" in str(exc_info.value) or "ISO" in str(exc_info.value)

        # 5. Active Configuration Soft-Delete Guard
        valid_config = await service.create_configuration(HRConfigurationCreate(
            organization_name="Valid Active Org",
            organization_code=org_code,
            is_active=True,
        ))
        with pytest.raises(Exception) as exc_info:
            await service.delete_configuration(valid_config.id)
        assert "ACTIVE_CONFIG_DELETION_PROHIBITED" in str(exc_info.value) or "active" in str(exc_info.value)


@pytest.mark.asyncio
async def test_hr_config_singleton_activation():
    """
    Tests Singleton Active Configuration pattern:
    - Creating Config 1 (active) -> Config 1 active
    - Creating Config 2 (active) -> Config 2 active, Config 1 deactivated
    - Activating Config 1 -> Config 1 active, Config 2 deactivated
    """
    async with AsyncSessionLocal() as session:
        service = HRConfigurationService(session)
        org_code = f"ORG-SING-{uuid.uuid4().hex[:6]}"

        cfg1 = await service.create_configuration(HRConfigurationCreate(
            organization_name="Single Org Policy 1",
            organization_code=org_code,
            timezone="UTC",
            is_active=True,
        ))
        assert cfg1.is_active is True

        cfg2 = await service.create_configuration(HRConfigurationCreate(
            organization_name="Single Org Policy 2",
            organization_code=org_code,
            timezone="Asia/Kolkata",
            is_active=True,
        ))
        assert cfg2.is_active is True

        cfg1_refreshed = await service.get_configuration_by_id(cfg1.id)
        assert cfg1_refreshed.is_active is False

        # Reactivate Config 1
        activated_cfg1 = await service.activate_configuration(cfg1.id)
        assert activated_cfg1.is_active is True

        cfg2_refreshed = await service.get_configuration_by_id(cfg2.id)
        assert cfg2_refreshed.is_active is False


@pytest.mark.asyncio
async def test_hr_config_api_endpoints(async_client: AsyncClient, admin_token: str):
    """
    Tests complete HR Configuration RESTful API endpoints:
    - POST /api/v1/hr/configuration
    - GET /api/v1/hr/configuration
    - GET /api/v1/hr/configurations/{id}
    - PUT /api/v1/hr/configuration/{id}
    - PATCH /api/v1/hr/configuration/{id}/activate
    - DELETE /api/v1/hr/configuration/{id}
    - PATCH /api/v1/hr/configuration/{id}/restore
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    celery_app.conf.task_always_eager = True
    org_code = f"ORG-API-{uuid.uuid4().hex[:6]}"

    # 1. POST /api/v1/hr/configuration
    res = await async_client.post(
        "/api/v1/hr/configuration",
        json={
            "organization_name": "API Enterprise",
            "organization_code": org_code,
            "timezone": "Asia/Kolkata",
            "country": "India",
            "currency": "INR",
            "standard_working_hours_per_day": 8.0,
            "standard_working_days_per_week": 5,
            "weekend_configuration": ["Saturday", "Sunday"],
            "default_shift_name": "Day Shift",
            "grace_period_minutes": 15,
            "minimum_working_hours": 4.0,
            "default_probation_period_days": 90,
            "leave_year_start_month": 1,
            "payroll_cycle": "Monthly",
            "fiscal_year_start_month": 4,
            "is_active": True,
        },
        headers=headers,
    )
    assert res.status_code == 201
    cfg_data = res.json()
    cfg_id = cfg_data["id"]
    assert cfg_data["organization_code"] == org_code
    assert cfg_data["is_active"] is True

    # 2. GET /api/v1/hr/configuration
    res = await async_client.get(f"/api/v1/hr/configuration?organization_code={org_code}", headers=headers)
    assert res.status_code == 200
    assert res.json()["id"] == cfg_id

    # 3. GET /api/v1/hr/configurations/{id}
    res = await async_client.get(f"/api/v1/hr/configurations/{cfg_id}", headers=headers)
    assert res.status_code == 200
    assert res.json()["organization_name"] == "API Enterprise"

    # 4. PUT /api/v1/hr/configuration/{id}
    res = await async_client.put(
        f"/api/v1/hr/configuration/{cfg_id}",
        json={"organization_name": "API Global Enterprise", "grace_period_minutes": 20},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["organization_name"] == "API Global Enterprise"
    assert res.json()["grace_period_minutes"] == 20

    # Create a 2nd active config (deactivates 1st config)
    res2 = await async_client.post(
        "/api/v1/hr/configuration",
        json={
            "organization_name": "API Enterprise Policy 2",
            "organization_code": org_code,
            "timezone": "UTC",
            "is_active": True,
        },
        headers=headers,
    )
    assert res2.status_code == 201
    cfg2_id = res2.json()["id"]

    # 5. PATCH /api/v1/hr/configuration/{id}/activate (Activate 1st config)
    res = await async_client.patch(f"/api/v1/hr/configuration/{cfg_id}/activate", headers=headers)
    assert res.status_code == 200
    assert res.json()["is_active"] is True

    # 6. DELETE /api/v1/hr/configuration/{id} (Delete 2nd now-inactive config)
    res = await async_client.delete(f"/api/v1/hr/configuration/{cfg2_id}", headers=headers)
    assert res.status_code == 200
    assert res.json()["is_deleted"] is True

    # 7. PATCH /api/v1/hr/configuration/{id}/restore
    res = await async_client.patch(f"/api/v1/hr/configuration/{cfg2_id}/restore", headers=headers)
    assert res.status_code == 200
    assert res.json()["is_deleted"] is False


@pytest.mark.asyncio
async def test_hr_config_rbac_unauthorized(async_client: AsyncClient):
    """Tests 401 Unauthorized for unauthenticated requests."""
    res = await async_client.get("/api/v1/hr/configuration")
    assert res.status_code == 401

    res = await async_client.post("/api/v1/hr/configuration", json={"organization_name": "Unauthorized", "organization_code": "UNAUTH"})
    assert res.status_code == 401
