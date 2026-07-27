import datetime
from unittest.mock import patch
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.exceptions.base import ApnaERPException
from app.models.leave_type import LeaveType
from app.models.user import User
from app.repositories.leave_type import leave_type_repository
from app.repositories.user import user_repository
from app.schemas.leave_type import LeaveTypeCreate, LeaveTypeUpdate
from app.services.leave_type import LeaveTypeService


@pytest.fixture(autouse=True)
def mock_celery_task():
    """Autouse fixture to mock Celery notification task dispatch in unit tests."""
    with patch("app.services.leave_type.send_leave_policy_change_notification_task.delay") as mock_delay:
        yield mock_delay


@pytest_asyncio.fixture
async def admin_auth_token(async_client: AsyncClient):
    """Fixture returning JWT auth token for Super Admin."""
    email = f"leaveadmin_{uuid.uuid4().hex[:6]}@example.com"
    reg_resp = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": f"leaveadmin_{uuid.uuid4().hex[:6]}",
            "password": "AdminPassword123!",
            "full_name": "Leave Admin",
        },
    )
    user_id = uuid.UUID(reg_resp.json()["id"])

    async with AsyncSessionLocal() as session:
        user = await user_repository.get_by_id(session, user_id)
        if user:
            user.is_superuser = True
            await session.commit()

    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={
            "username_or_email": reg_resp.json()["username"],
            "password": "AdminPassword123!",
        },
    )
    return login_resp.json()["access_token"]


@pytest.mark.asyncio
async def test_leave_type_create_and_read():
    """Tests creating a LeaveType and retrieving it via service and cache."""
    async with AsyncSessionLocal() as session:
        service = LeaveTypeService(session)

        code = f"ANNUAL-{uuid.uuid4().hex[:4]}"
        name = f"Annual Leave {uuid.uuid4().hex[:4]}"

        created = await service.create_leave_type(
            LeaveTypeCreate(
                code=code,
                name=name,
                description="Standard paid annual leave allowance",
                is_paid=True,
                requires_approval=True,
                allow_half_day=True,
                allow_negative_balance=False,
                annual_allocation=21.0,
                carry_forward_allowed=True,
                max_carry_forward=5.0,
                max_consecutive_days=14,
                is_active=True,
            )
        )

        assert created.id is not None
        assert created.code == code
        assert created.name == name
        assert created.annual_allocation == 21.0
        assert created.carry_forward_allowed is True
        assert created.max_carry_forward == 5.0

        # Read back via service (populates Redis cache)
        fetched = await service.get_leave_type_by_id(created.id)
        assert fetched.id == created.id
        assert fetched.code == code


@pytest.mark.asyncio
async def test_leave_type_validation_business_rules():
    """Tests business rule validations: code/name uniqueness, carry forward limits."""
    async with AsyncSessionLocal() as session:
        service = LeaveTypeService(session)

        code = f"SICK-{uuid.uuid4().hex[:4]}"
        name = f"Sick Leave {uuid.uuid4().hex[:4]}"

        await service.create_leave_type(
            LeaveTypeCreate(
                code=code,
                name=name,
                annual_allocation=10.0,
                carry_forward_allowed=False,
                max_carry_forward=0.0,
            )
        )

        # 1. Duplicate Code Rejection
        with pytest.raises(ApnaERPException) as exc_info:
            await service.create_leave_type(
                LeaveTypeCreate(
                    code=code,
                    name=f"Other Sick Leave {uuid.uuid4().hex[:4]}",
                    annual_allocation=10.0,
                )
            )
        assert exc_info.value.error_code == "DUPLICATE_LEAVE_CODE"

        # 2. Duplicate Name Rejection
        with pytest.raises(ApnaERPException) as exc_info:
            await service.create_leave_type(
                LeaveTypeCreate(
                    code=f"SICK2-{uuid.uuid4().hex[:4]}",
                    name=name,
                    annual_allocation=10.0,
                )
            )
        assert exc_info.value.error_code == "DUPLICATE_LEAVE_NAME"

        # 3. Carry Forward > Annual Allocation Rejection
        with pytest.raises(ApnaERPException) as exc_info:
            await service.create_leave_type(
                LeaveTypeCreate(
                    code=f"CASUAL-{uuid.uuid4().hex[:4]}",
                    name=f"Casual Leave {uuid.uuid4().hex[:4]}",
                    annual_allocation=5.0,
                    carry_forward_allowed=True,
                    max_carry_forward=10.0,  # 10 > 5 -> invalid
                )
            )
        assert exc_info.value.error_code == "INVALID_CARRY_FORWARD"

        # 4. Carry Forward > 0 when carry_forward_allowed is False
        with pytest.raises(ApnaERPException) as exc_info:
            await service.create_leave_type(
                LeaveTypeCreate(
                    code=f"MATERNITY-{uuid.uuid4().hex[:4]}",
                    name=f"Maternity Leave {uuid.uuid4().hex[:4]}",
                    annual_allocation=90.0,
                    carry_forward_allowed=False,
                    max_carry_forward=5.0,  # Allowed=False but max > 0 -> invalid
                )
            )
        assert exc_info.value.error_code == "INVALID_CARRY_FORWARD"


@pytest.mark.asyncio
async def test_leave_type_update_and_restore():
    """Tests updating, soft-deleting, and restoring a LeaveType."""
    async with AsyncSessionLocal() as session:
        service = LeaveTypeService(session)

        code = f"CASUAL-{uuid.uuid4().hex[:4]}"
        name = f"Casual Leave {uuid.uuid4().hex[:4]}"

        leave_type = await service.create_leave_type(
            LeaveTypeCreate(
                code=code,
                name=name,
                annual_allocation=12.0,
                carry_forward_allowed=False,
                max_carry_forward=0.0,
            )
        )

        # Update allocation
        updated = await service.update_leave_type(
            id=leave_type.id,
            data=LeaveTypeUpdate(
                annual_allocation=14.0,
                description="Updated annual allocation to 14 days",
            ),
        )
        assert updated.annual_allocation == 14.0
        assert updated.description == "Updated annual allocation to 14 days"

        # Soft delete
        deleted = await service.delete_leave_type(leave_type.id)
        assert deleted is True

        # Fetching deleted should raise 404
        with pytest.raises(ApnaERPException) as exc_info:
            await service.get_leave_type_by_id(leave_type.id)
        assert exc_info.value.error_code == "LEAVE_TYPE_NOT_FOUND"

        # Restore
        restored = await service.restore_leave_type(leave_type.id)
        assert restored.is_deleted is False

        # Fetch after restore
        refetched = await service.get_leave_type_by_id(leave_type.id)
        assert refetched.id == leave_type.id


@pytest.mark.asyncio
async def test_leave_type_api_full_workflow(async_client: AsyncClient, admin_auth_token: str):
    """Tests full HTTP REST API lifecycle for Leave Types."""
    headers = {"Authorization": f"Bearer {admin_auth_token}"}

    code = f"WFH-{uuid.uuid4().hex[:4]}"
    name = f"Work From Home {uuid.uuid4().hex[:4]}"

    # 1. Create Leave Type
    create_resp = await async_client.post(
        "/api/v1/leave-types",
        json={
            "code": code,
            "name": name,
            "description": "Remote working policy allocation",
            "is_paid": True,
            "requires_approval": True,
            "allow_half_day": True,
            "annual_allocation": 24.0,
            "carry_forward_allowed": False,
            "max_carry_forward": 0.0,
            "max_consecutive_days": 5,
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    leave_id = created_data["id"]
    assert created_data["code"] == code

    # 2. Get Leave Type by ID
    get_resp = await async_client.get(f"/api/v1/leave-types/{leave_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == name

    # 3. List Leave Types
    list_resp = await async_client.get("/api/v1/leave-types", headers=headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1

    # 4. Update Leave Type
    update_resp = await async_client.put(
        f"/api/v1/leave-types/{leave_id}",
        json={"annual_allocation": 30.0, "description": "Increased WFH days"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["annual_allocation"] == 30.0

    # 5. Delete Leave Type
    del_resp = await async_client.delete(f"/api/v1/leave-types/{leave_id}", headers=headers)
    assert del_resp.status_code == 204

    # 6. Restore Leave Type
    restore_resp = await async_client.patch(f"/api/v1/leave-types/{leave_id}/restore", headers=headers)
    assert restore_resp.status_code == 200
    assert restore_resp.json()["is_deleted"] is False
