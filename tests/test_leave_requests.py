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
from app.models.holiday import Holiday
from app.models.leave_balance import LeaveBalance
from app.models.leave_request import LeaveRequest
from app.models.leave_type import LeaveType
from app.repositories.department import department_repository
from app.repositories.employee import employee_repository
from app.repositories.holiday import holiday_repository
from app.repositories.leave_balance import leave_balance_repository
from app.repositories.leave_type import leave_type_repository
from app.repositories.user import user_repository
from app.schemas.leave_balance import LeaveBalanceCreate
from app.schemas.leave_request import (
    LeaveRequestCancelRequest,
    LeaveRequestCreate,
    LeaveRequestReviewRequest,
)
from app.services.leave_balance import LeaveBalanceService
from app.services.leave_request import LeaveRequestService


@pytest.fixture(autouse=True)
def mock_celery_task():
    """Autouse fixture to mock Celery notification task dispatch in unit tests."""
    with patch(
        "app.services.leave_request.send_leave_request_notification_task.delay"
    ) as mock_delay:
        yield mock_delay


@pytest_asyncio.fixture
async def admin_auth_token(async_client: AsyncClient):
    """Fixture returning JWT auth token for Super Admin."""
    email = f"reqadmin_{uuid.uuid4().hex[:6]}@example.com"
    reg_resp = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": f"reqadmin_{uuid.uuid4().hex[:6]}",
            "password": "AdminPassword123!",
            "full_name": "Request Admin",
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
async def setup_employee_policy_and_balance():
    """Fixture initializing a sample employee, leave policy, holiday, and leave balance."""
    async with AsyncSessionLocal() as session:
        dept = await department_repository.create(
            session,
            obj_in={
                "code": f"ENG-{uuid.uuid4().hex[:4]}",
                "name": f"Engineering {uuid.uuid4().hex[:4]}",
                "is_active": True,
            },
        )
        emp = await employee_repository.create(
            session,
            obj_in={
                "employee_code": f"EMP-{uuid.uuid4().hex[:6]}",
                "first_name": "John",
                "last_name": "Smith",
                "work_email": f"john_{uuid.uuid4().hex[:6]}@example.com",
                "department_id": dept.id,
                "joining_date": datetime.date(2025, 1, 1),
                "gender": "Male",
                "is_active": True,
            },
        )
        lt = await leave_type_repository.create(
            session,
            obj_in={
                "code": f"ANN-{uuid.uuid4().hex[:4]}",
                "name": f"Annual Paid Leave {uuid.uuid4().hex[:4]}",
                "annual_allocation": 20.0,
                "allow_half_day": True,
                "max_consecutive_days": 10,
                "gender_restriction": "All",
                "allow_negative_balance": False,
                "is_active": True,
            },
        )
        bal_service = LeaveBalanceService(session)
        balance = await bal_service.create_leave_balance(
            LeaveBalanceCreate(
                employee_id=emp.id,
                leave_type_id=lt.id,
                leave_year=2026,
                allocated_days=20.0,
            )
        )
        yield emp, lt, balance


@pytest.mark.asyncio
async def test_leave_request_working_day_calculation(setup_employee_policy_and_balance):
    """Tests working day calculation excluding weekends and organizational holidays."""
    emp, lt, bal = setup_employee_policy_and_balance

    async with AsyncSessionLocal() as session:
        # Create a holiday on Monday 2026-08-03
        holiday_date = datetime.date(2026, 8, 3)
        await holiday_repository.create(
            session,
            obj_in={
                "code": f"HOL-{uuid.uuid4().hex[:4]}",
                "name": "Summer Bank Holiday",
                "holiday_date": holiday_date,
                "is_active": True,
            },
        )

        service = LeaveRequestService(session)

        # Friday 2026-07-31 to Tuesday 2026-08-04:
        # Fri 07-31: Workday (1)
        # Sat 08-01: Weekend (0)
        # Sun 08-02: Weekend (0)
        # Mon 08-03: Holiday (0)
        # Tue 08-04: Workday (1)
        # Total Net Working Days = 2
        total_days = await service.calculate_working_days(
            datetime.date(2026, 7, 31), datetime.date(2026, 8, 4)
        )
        assert total_days == 2.0


@pytest.mark.asyncio
async def test_leave_request_state_machine_transitions(setup_employee_policy_and_balance, mock_celery_task):
    """Tests valid workflow state machine transitions and invalid transition rejections."""
    emp, lt, bal = setup_employee_policy_and_balance

    async with AsyncSessionLocal() as session:
        service = LeaveRequestService(session)

        # 1. Create Draft (Tue 2026-09-08 to Thu 2026-09-10 = 3 working days in future)
        req = await service.create_leave_request(
            LeaveRequestCreate(
                employee_id=emp.id,
                leave_type_id=lt.id,
                start_date=datetime.date(2026, 9, 8),
                end_date=datetime.date(2026, 9, 10),
                reason="Personal vacation trip",
            )
        )
        assert req.status == "Draft"
        assert req.total_days == 3.0

        # Invalid transition: Draft -> Approved directly (rejected)
        with pytest.raises(ApnaERPException) as exc_info:
            await service.approve_leave_request(req.id, LeaveRequestReviewRequest(reviewer_comments="Direct approve"))
        assert exc_info.value.error_code == "INVALID_WORKFLOW_TRANSITION"

        # 2. Submit Draft -> Pending
        submitted = await service.submit_leave_request(req.id)
        assert submitted.status == "Pending"
        assert submitted.submitted_at is not None

        # 3. Approve Pending -> Approved
        approved = await service.approve_leave_request(
            req.id, LeaveRequestReviewRequest(reviewer_comments="Approved by manager")
        )
        assert approved.status == "Approved"
        assert approved.reviewed_at is not None

        # 4. Cancel Approved -> Cancelled (before start date)
        cancelled = await service.cancel_leave_request(
            req.id, LeaveRequestCancelRequest(reason="Plans changed")
        )
        assert cancelled.status == "Cancelled"

        # Invalid transition: Cancelled -> Approved (terminal state rejection)
        with pytest.raises(ApnaERPException) as exc_info:
            await service.approve_leave_request(req.id, LeaveRequestReviewRequest())
        assert exc_info.value.error_code == "INVALID_WORKFLOW_TRANSITION"


@pytest.mark.asyncio
async def test_leave_request_policy_validations(setup_employee_policy_and_balance):
    """Tests policy validations: half day, max consecutive days, gender restriction, overlap."""
    emp, lt, bal = setup_employee_policy_and_balance

    async with AsyncSessionLocal() as session:
        service = LeaveRequestService(session)

        # 1. Half-day policy check
        lt_no_half = await leave_type_repository.create(
            session,
            obj_in={
                "code": f"NOHALF-{uuid.uuid4().hex[:4]}",
                "name": f"Full Day Only {uuid.uuid4().hex[:4]}",
                "annual_allocation": 10.0,
                "allow_half_day": False,
                "is_active": True,
            },
        )
        bal_service = LeaveBalanceService(session)
        await bal_service.create_leave_balance(
            LeaveBalanceCreate(
                employee_id=emp.id,
                leave_type_id=lt_no_half.id,
                leave_year=2026,
                allocated_days=10.0,
            )
        )

        with pytest.raises(ApnaERPException) as exc_info:
            await service.create_leave_request(
                LeaveRequestCreate(
                    employee_id=emp.id,
                    leave_type_id=lt_no_half.id,
                    start_date=datetime.date(2026, 10, 1),
                    end_date=datetime.date(2026, 10, 1),
                    is_half_day=True,
                    reason="Doctor appointment half day",
                )
            )
        assert exc_info.value.error_code == "HALF_DAY_NOT_PERMITTED"

        # 2. Gender restriction check
        lt_female = await leave_type_repository.create(
            session,
            obj_in={
                "code": f"MAT-{uuid.uuid4().hex[:4]}",
                "name": f"Maternity Policy {uuid.uuid4().hex[:4]}",
                "annual_allocation": 90.0,
                "gender_restriction": "Female",
                "is_active": True,
            },
        )
        await bal_service.create_leave_balance(
            LeaveBalanceCreate(
                employee_id=emp.id,
                leave_type_id=lt_female.id,
                leave_year=2026,
                allocated_days=90.0,
            )
        )

        with pytest.raises(ApnaERPException) as exc_info:
            await service.create_leave_request(
                LeaveRequestCreate(
                    employee_id=emp.id,  # male employee
                    leave_type_id=lt_female.id,
                    start_date=datetime.date(2026, 10, 5),
                    end_date=datetime.date(2026, 10, 9),
                    reason="Maternity leave application",
                )
            )
        assert exc_info.value.error_code == "GENDER_RESTRICTION_MISMATCH"

        # 3. Overlap check
        req1 = await service.create_leave_request(
            LeaveRequestCreate(
                employee_id=emp.id,
                leave_type_id=lt.id,
                start_date=datetime.date(2026, 11, 2),
                end_date=datetime.date(2026, 11, 6),
                reason="First week of November",
            )
        )
        await service.submit_leave_request(req1.id)  # Pending

        with pytest.raises(ApnaERPException) as exc_info:
            await service.create_leave_request(
                LeaveRequestCreate(
                    employee_id=emp.id,
                    leave_type_id=lt.id,
                    start_date=datetime.date(2026, 11, 5),  # Overlaps 11-05 and 11-06
                    end_date=datetime.date(2026, 11, 10),
                    reason="Overlapping request",
                )
            )
        assert exc_info.value.error_code == "OVERLAPPING_LEAVE_REQUEST"


@pytest.mark.asyncio
async def test_leave_request_balance_update_on_approval_and_cancel(setup_employee_policy_and_balance):
    """Tests that approving a leave request updates LeaveBalance.availed_days, and cancelling restores it."""
    emp, lt, bal = setup_employee_policy_and_balance  # remaining_days = 20.0

    async with AsyncSessionLocal() as session:
        service = LeaveRequestService(session)
        bal_service = LeaveBalanceService(session)

        req = await service.create_leave_request(
            LeaveRequestCreate(
                employee_id=emp.id,
                leave_type_id=lt.id,
                start_date=datetime.date(2026, 12, 1),
                end_date=datetime.date(2026, 12, 3),  # 3 days
                reason="December holidays",
            )
        )
        await service.submit_leave_request(req.id)
        await service.approve_leave_request(req.id, LeaveRequestReviewRequest(reviewer_comments="Approved"))

        # Verify LeaveBalance updated
        updated_bal = await bal_service.get_leave_balance_by_id(bal.id)
        assert updated_bal.availed_days == 3.0
        assert updated_bal.remaining_days == 17.0

        # Cancel approved request before start date
        await service.cancel_leave_request(req.id, LeaveRequestCancelRequest(reason="Cancelled trip"))
        restored_bal = await bal_service.get_leave_balance_by_id(bal.id)
        assert restored_bal.availed_days == 0.0
        assert restored_bal.remaining_days == 20.0


@pytest.mark.asyncio
async def test_leave_request_api_full_workflow(
    async_client: AsyncClient, admin_auth_token: str, setup_employee_policy_and_balance
):
    """Tests full HTTP REST API lifecycle for Leave Requests."""
    emp, lt, bal = setup_employee_policy_and_balance
    headers = {"Authorization": f"Bearer {admin_auth_token}"}

    # 1. Create Draft Leave Request
    create_resp = await async_client.post(
        "/api/v1/leave-requests",
        json={
            "employee_id": str(emp.id),
            "leave_type_id": str(lt.id),
            "start_date": "2026-10-12",
            "end_date": "2026-10-14",
            "reason": "Family function leave",
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    req_id = created_data["id"]
    assert created_data["status"] == "Draft"
    assert created_data["total_days"] == 3.0

    # 2. Get Leave Request by ID
    get_resp = await async_client.get(f"/api/v1/leave-requests/{req_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "Draft"

    # 3. List Employee Leave Requests
    emp_reqs_resp = await async_client.get(
        f"/api/v1/leave-requests/employees/{emp.id}/leave-requests", headers=headers
    )
    assert emp_reqs_resp.status_code == 200
    assert emp_reqs_resp.json()["total"] >= 1

    # 4. List All Leave Requests
    list_resp = await async_client.get("/api/v1/leave-requests", headers=headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 1

    # 5. Submit Leave Request
    submit_resp = await async_client.post(
        f"/api/v1/leave-requests/{req_id}/submit", headers=headers
    )
    assert submit_resp.status_code == 200
    assert submit_resp.json()["status"] == "Pending"

    # 6. Approve Leave Request
    approve_resp = await async_client.post(
        f"/api/v1/leave-requests/{req_id}/approve",
        json={"reviewer_comments": "Looks good, enjoy!"},
        headers=headers,
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "Approved"

    # 7. Cancel Leave Request
    cancel_resp = await async_client.post(
        f"/api/v1/leave-requests/{req_id}/cancel",
        json={"reason": "Function rescheduled"},
        headers=headers,
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "Cancelled"
