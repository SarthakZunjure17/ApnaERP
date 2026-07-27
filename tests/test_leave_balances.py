import datetime
from unittest.mock import patch
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.db.session import AsyncSessionLocal
from app.exceptions.base import ApnaERPException
from app.models.department import Department
from app.models.employee import Employee
from app.models.leave_balance import LeaveBalance
from app.models.leave_type import LeaveType
from app.repositories.department import department_repository
from app.repositories.employee import employee_repository
from app.repositories.leave_type import leave_type_repository
from app.repositories.user import user_repository
from app.schemas.leave_balance import (
    LeaveBalanceAdjustmentRequest,
    LeaveBalanceCreate,
    LeaveBalanceUpdate,
)
from app.schemas.leave_type import LeaveTypeCreate
from app.services.leave_balance import LeaveBalanceService


@pytest.fixture(autouse=True)
def mock_celery_task():
    """Autouse fixture to mock Celery notification task dispatch in unit tests."""
    with patch(
        "app.services.leave_balance.send_leave_balance_adjustment_notification_task.delay"
    ) as mock_delay:
        yield mock_delay


@pytest_asyncio.fixture
async def admin_auth_token(async_client: AsyncClient):
    """Fixture returning JWT auth token for Super Admin."""
    email = f"balanceadmin_{uuid.uuid4().hex[:6]}@example.com"
    reg_resp = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": f"balanceadmin_{uuid.uuid4().hex[:6]}",
            "password": "AdminPassword123!",
            "full_name": "Balance Admin",
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


@pytest_asyncio.fixture
async def sample_employee_and_leave_type():
    """Fixture creating a sample department, employee, and leave type."""
    async with AsyncSessionLocal() as session:
        dept = await department_repository.create(
            session,
            obj_in={
                "code": f"HR-{uuid.uuid4().hex[:4]}",
                "name": f"HR Department {uuid.uuid4().hex[:4]}",
                "is_active": True,
            },
        )
        emp = await employee_repository.create(
            session,
            obj_in={
                "employee_code": f"EMP-{uuid.uuid4().hex[:6]}",
                "first_name": "Jane",
                "last_name": "Doe",
                "work_email": f"jane_{uuid.uuid4().hex[:6]}@example.com",
                "department_id": dept.id,
                "joining_date": datetime.date(2025, 1, 1),
                "is_active": True,
            },
        )
        lt = await leave_type_repository.create(
            session,
            obj_in={
                "code": f"AL-{uuid.uuid4().hex[:4]}",
                "name": f"Annual Leave {uuid.uuid4().hex[:4]}",
                "annual_allocation": 20.0,
                "carry_forward_allowed": True,
                "max_carry_forward": 5.0,
                "allow_negative_balance": False,
                "is_active": True,
            },
        )
        yield emp, lt


@pytest.mark.asyncio
async def test_leave_balance_create_and_derivation(sample_employee_and_leave_type):
    """Tests balance creation and mathematical derivation of remaining_days."""
    emp, lt = sample_employee_and_leave_type

    async with AsyncSessionLocal() as session:
        service = LeaveBalanceService(session)

        # Formula: opening (10) + allocated (20) + earned (2) + cf (3) - availed (5) - encashed (2) = 28.0
        created = await service.create_leave_balance(
            LeaveBalanceCreate(
                employee_id=emp.id,
                leave_type_id=lt.id,
                leave_year=2026,
                opening_balance=10.0,
                allocated_days=20.0,
                earned_days=2.0,
                carried_forward_days=3.0,
                availed_days=5.0,
                encashed_days=2.0,
            )
        )

        assert created.id is not None
        assert created.employee_id == emp.id
        assert created.leave_type_id == lt.id
        assert created.leave_year == 2026
        assert created.remaining_days == 28.0


@pytest.mark.asyncio
async def test_leave_balance_uniqueness_constraint(sample_employee_and_leave_type):
    """Tests that duplicate balances for same employee + leave_type + leave_year are rejected."""
    emp, lt = sample_employee_and_leave_type

    async with AsyncSessionLocal() as session:
        service = LeaveBalanceService(session)

        await service.create_leave_balance(
            LeaveBalanceCreate(
                employee_id=emp.id,
                leave_type_id=lt.id,
                leave_year=2026,
                allocated_days=20.0,
            )
        )

        with pytest.raises(ApnaERPException) as exc_info:
            await service.create_leave_balance(
                LeaveBalanceCreate(
                    employee_id=emp.id,
                    leave_type_id=lt.id,
                    leave_year=2026,
                    allocated_days=10.0,
                )
            )
        assert exc_info.value.error_code == "DUPLICATE_LEAVE_BALANCE"


@pytest.mark.asyncio
async def test_leave_balance_negative_balance_rules(sample_employee_and_leave_type):
    """Tests negative balance policy enforcement."""
    emp, lt = sample_employee_and_leave_type

    async with AsyncSessionLocal() as session:
        service = LeaveBalanceService(session)

        # 1. When allow_negative_balance=False, derived remaining < 0 must be rejected
        with pytest.raises(ApnaERPException) as exc_info:
            await service.create_leave_balance(
                LeaveBalanceCreate(
                    employee_id=emp.id,
                    leave_type_id=lt.id,
                    leave_year=2026,
                    allocated_days=5.0,
                    availed_days=10.0,  # 5 - 10 = -5 -> rejected
                )
            )
        assert exc_info.value.error_code == "NEGATIVE_LEAVE_BALANCE"

        # 2. When allow_negative_balance=True, negative balance is permitted
        lt2 = await leave_type_repository.create(
            session,
            obj_in={
                "code": f"NEG-{uuid.uuid4().hex[:4]}",
                "name": f"Negative Permitted Leave {uuid.uuid4().hex[:4]}",
                "annual_allocation": 10.0,
                "allow_negative_balance": True,
                "is_active": True,
            },
        )

        allowed_neg = await service.create_leave_balance(
            LeaveBalanceCreate(
                employee_id=emp.id,
                leave_type_id=lt2.id,
                leave_year=2026,
                allocated_days=5.0,
                availed_days=10.0,
            )
        )
        assert allowed_neg.remaining_days == -5.0


@pytest.mark.asyncio
async def test_leave_balance_carry_forward_validation(sample_employee_and_leave_type):
    """Tests carry forward policy validations against LeaveType limits."""
    emp, lt = sample_employee_and_leave_type  # max_carry_forward = 5.0

    async with AsyncSessionLocal() as session:
        service = LeaveBalanceService(session)

        with pytest.raises(ApnaERPException) as exc_info:
            await service.create_leave_balance(
                LeaveBalanceCreate(
                    employee_id=emp.id,
                    leave_type_id=lt.id,
                    leave_year=2026,
                    carried_forward_days=10.0,  # 10 > 5 -> rejected
                )
            )
        assert exc_info.value.error_code == "INVALID_CARRY_FORWARD"


@pytest.mark.asyncio
async def test_leave_balance_adjustments_and_celery(sample_employee_and_leave_type, mock_celery_task):
    """Tests manual leave balance adjustments and Celery notification dispatch."""
    emp, lt = sample_employee_and_leave_type

    async with AsyncSessionLocal() as session:
        service = LeaveBalanceService(session)

        balance = await service.create_leave_balance(
            LeaveBalanceCreate(
                employee_id=emp.id,
                leave_type_id=lt.id,
                leave_year=2026,
                allocated_days=20.0,
            )
        )
        assert balance.remaining_days == 20.0

        # Adjust availed days by +3
        adjusted = await service.adjust_leave_balance(
            id=balance.id,
            data=LeaveBalanceAdjustmentRequest(
                adjustment_type="availed",
                adjustment_days=3.0,
                reason="Correction for emergency leave taken in January",
            ),
        )
        assert adjusted.availed_days == 3.0
        assert adjusted.remaining_days == 17.0
        mock_celery_task.assert_called_once()


@pytest.mark.asyncio
async def test_leave_balance_soft_delete_and_restore(sample_employee_and_leave_type):
    """Tests soft deletion and restoration of LeaveBalance entity."""
    emp, lt = sample_employee_and_leave_type

    async with AsyncSessionLocal() as session:
        service = LeaveBalanceService(session)

        balance = await service.create_leave_balance(
            LeaveBalanceCreate(
                employee_id=emp.id,
                leave_type_id=lt.id,
                leave_year=2026,
                allocated_days=15.0,
            )
        )

        deleted = await service.delete_leave_balance(balance.id)
        assert deleted is True

        with pytest.raises(ApnaERPException) as exc_info:
            await service.get_leave_balance_by_id(balance.id)
        assert exc_info.value.error_code == "LEAVE_BALANCE_NOT_FOUND"

        restored = await service.restore_leave_balance(balance.id)
        assert restored.is_deleted is False


@pytest.mark.asyncio
async def test_leave_balance_api_full_workflow(
    async_client: AsyncClient, admin_auth_token: str, sample_employee_and_leave_type
):
    """Tests full HTTP REST API lifecycle for Leave Balances."""
    emp, lt = sample_employee_and_leave_type
    headers = {"Authorization": f"Bearer {admin_auth_token}"}

    # 1. Create Leave Balance
    create_resp = await async_client.post(
        "/api/v1/leave-balances",
        json={
            "employee_id": str(emp.id),
            "leave_type_id": str(lt.id),
            "leave_year": 2026,
            "opening_balance": 5.0,
            "allocated_days": 20.0,
            "carried_forward_days": 2.0,
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    bal_id = created_data["id"]
    assert created_data["remaining_days"] == 27.0

    # 2. Get Leave Balance by ID
    get_resp = await async_client.get(f"/api/v1/leave-balances/{bal_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["remaining_days"] == 27.0

    # 3. Get Employee Leave Balances
    emp_bal_resp = await async_client.get(
        f"/api/v1/leave-balances/employees/{emp.id}/leave-balances", headers=headers
    )
    assert emp_bal_resp.status_code == 200
    assert emp_bal_resp.json()["total"] >= 1

    # 4. List Leave Balances
    list_resp = await async_client.get("/api/v1/leave-balances", headers=headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1

    # 5. Update Leave Balance
    update_resp = await async_client.put(
        f"/api/v1/leave-balances/{bal_id}",
        json={"allocated_days": 25.0},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["remaining_days"] == 32.0

    # 6. Adjust Leave Balance
    adjust_resp = await async_client.patch(
        f"/api/v1/leave-balances/{bal_id}/adjust",
        json={
            "adjustment_type": "availed",
            "adjustment_days": 4.0,
            "reason": "Approved sick leave adjustment",
        },
        headers=headers,
    )
    assert adjust_resp.status_code == 200
    assert adjust_resp.json()["availed_days"] == 4.0
    assert adjust_resp.json()["remaining_days"] == 28.0

    # 7. Delete Leave Balance
    del_resp = await async_client.delete(f"/api/v1/leave-balances/{bal_id}", headers=headers)
    assert del_resp.status_code == 204

    # 8. Restore Leave Balance
    restore_resp = await async_client.patch(
        f"/api/v1/leave-balances/{bal_id}/restore", headers=headers
    )
    assert restore_resp.status_code == 200
    assert restore_resp.json()["is_deleted"] is False
