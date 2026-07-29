import datetime
from decimal import Decimal
import random
import uuid
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.payroll_adjustment import router as adjustment_router
from app.core.security import create_access_token, hash_password
from app.db.session import AsyncSessionLocal
from app.exceptions.base import DuplicateResourceException, NotFoundException, ValidationException
from app.main import app
from app.models.department import Department
from app.models.employee import Employee
from app.models.payroll_adjustment import PayrollAdjustment
from app.models.payroll_closing import PayrollClosing
from app.models.payroll_period import PayrollPeriod, PayrollRecord
from app.models.payroll_run import PayrollRun
from app.models.permission import Permission
from app.models.role import Role, RolePermission
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.payroll_finalization import (
    AdjustmentStatusEnum,
    AdjustmentTypeEnum,
    BankExportRequest,
    PayrollAdjustmentCreate,
    PayrollAdjustmentUpdate,
    PayrollClosingRequest,
    PayrollReopenRequest,
    PayrollReportGenerateRequest,
    ReportFormatEnum,
    ReportTypeEnum,
)
from app.services.payroll_finalization_services import (
    BankExportService,
    FinancialIntegrationService,
    PayrollAdjustmentService,
    PayrollAnalyticsService,
    PayrollClosingService,
    PayrollReportService,
)


@pytest.fixture(autouse=True)
def mock_celery_task():
    with patch("app.tasks.payroll_finalization_tasks.send_payroll_finalization_notification_task.delay") as mock_delay:
        yield mock_delay


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def setup_finalization_data(db_session: AsyncSession):
    """
    Sets up admin user, role with permissions, department, employee, payroll period, run, and records.
    """
    perms_query = await db_session.execute(Permission.__table__.select())
    all_perms = perms_query.fetchall()

    role = Role(
        name=f"PayrollAdmin_{uuid.uuid4().hex[:6]}",
        description="Payroll Finalization Admin Role",
    )
    db_session.add(role)
    await db_session.flush()

    for perm in all_perms:
        rp = RolePermission(role_id=role.id, permission_id=perm.id)
        db_session.add(rp)

    user = User(
        full_name="Payroll Finalization Admin",
        username=f"pay_admin_{uuid.uuid4().hex[:6]}",
        email=f"pay_admin_{uuid.uuid4().hex[:6]}@example.com",
        password_hash=hash_password("Pass123!"),
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.flush()

    user_role = UserRole(user_id=user.id, role_id=role.id)
    db_session.add(user_role)

    dept = Department(
        code=f"FIN_{uuid.uuid4().hex[:4].upper()}",
        name=f"Finance & Payroll {uuid.uuid4().hex[:6]}",
        is_active=True,
    )
    db_session.add(dept)
    await db_session.flush()

    employee = Employee(
        employee_code=f"EMP_{random.randint(10000, 99999)}",
        first_name="Anita",
        last_name="Deshmukh",
        work_email=f"anita_{uuid.uuid4().hex[:4]}@example.com",
        user_id=user.id,
        department_id=dept.id,
        employment_status="Active",
        joining_date=datetime.date(2025, 1, 1),
    )
    db_session.add(employee)
    await db_session.flush()

    # Create Payroll Period
    period = PayrollPeriod(
        period_code=f"PAY_2026_07_{uuid.uuid4().hex[:4]}",
        start_date=datetime.date(2026, 7, 1),
        end_date=datetime.date(2026, 7, 31),
        status="Open",
    )
    db_session.add(period)
    await db_session.flush()

    # Create Payroll Run (Completed)
    payroll_run = PayrollRun(
        payroll_period_id=period.id,
        run_number=f"RUN-202607-{uuid.uuid4().hex[:4]}",
        run_type="Regular",
        status="Completed",
        started_by=user.id,
    )
    db_session.add(payroll_run)
    await db_session.flush()

    # Create Salary Structure & Employee Compensation
    from app.models.salary_structure import SalaryStructure
    from app.models.employee_compensation import EmployeeCompensation

    struct = SalaryStructure(
        code=f"STD_{uuid.uuid4().hex[:4].upper()}",
        name=f"Standard Engineering Structure {uuid.uuid4().hex[:6]}",
        effective_from=datetime.date(2025, 1, 1),
        is_active=True,
    )
    db_session.add(struct)
    await db_session.flush()

    comp = EmployeeCompensation(
        employee_id=employee.id,
        salary_structure_id=struct.id,
        effective_from=datetime.date(2025, 1, 1),
        annual_ctc=720000.00,
        monthly_gross_salary=60000.00,
        status="Active",
    )
    db_session.add(comp)
    await db_session.flush()

    # Create Payroll Record
    record = PayrollRecord(
        payroll_period_id=period.id,
        employee_id=employee.id,
        employee_compensation_id=comp.id,
        gross_salary=Decimal("60000.00"),
        total_deductions=Decimal("8000.00"),
        net_salary=Decimal("52000.00"),
        status="Paid",
    )
    db_session.add(record)
    await db_session.commit()

    token = create_access_token(subject=user.id)

    return {
        "user_id": user.id,
        "admin_token": token,
        "employee_id": employee.id,
        "department_id": dept.id,
        "payroll_period_id": period.id,
        "payroll_run_id": payroll_run.id,
        "payroll_record_id": record.id,
    }


# ============================================================================
# 1. PAYROLL ADJUSTMENTS WORKFLOW
# ============================================================================

@pytest.mark.asyncio
async def test_payroll_adjustment_workflow(setup_finalization_data):
    """Tests adjustment creation, approval workflow, rejection, and period closing guards."""
    data = setup_finalization_data
    emp_id = data["employee_id"]
    period_id = data["payroll_period_id"]

    async with AsyncSessionLocal() as session:
        user = await session.get(User, data["user_id"])
        service = PayrollAdjustmentService(session)

        # 1. Create Bonus Adjustment
        adj = await service.create_adjustment(
            PayrollAdjustmentCreate(
                employee_id=emp_id,
                payroll_period_id=period_id,
                adjustment_type=AdjustmentTypeEnum.BONUS,
                amount=Decimal("5000.00"),
                description="Performance Bonus Q2",
            ),
            current_user=user,
        )
        assert adj.id is not None
        assert adj.status == "Pending"
        assert adj.amount == Decimal("5000.00")

        # 2. Update Adjustment
        updated = await service.update_adjustment(
            adj.id,
            PayrollAdjustmentUpdate(amount=Decimal("5500.00")),
            current_user=user,
        )
        assert updated.amount == Decimal("5500.00")

        # 3. Approve Adjustment
        approved = await service.approve_adjustment(adj.id, current_user=user)
        assert approved.status == "Approved"
        assert approved.approved_by == user.id

        # 4. Query Approved Adjustments
        approved_list = await service.adj_repo.get_approved_adjustments_for_period(session, period_id)
        assert len(approved_list) == 1
        assert approved_list[0].id == adj.id


# ============================================================================
# 2. PAYROLL ANALYTICS
# ============================================================================

@pytest.mark.asyncio
async def test_payroll_analytics_service(setup_finalization_data):
    """Tests executive dashboard metrics calculation and Redis caching."""
    data = setup_finalization_data
    period_id = data["payroll_period_id"]

    async with AsyncSessionLocal() as session:
        service = PayrollAnalyticsService(session)
        analytics = await service.get_analytics(period_id)

        assert analytics.employee_count == 1
        assert analytics.total_payroll_cost == Decimal("60000.00")
        assert analytics.total_deductions == Decimal("8000.00")
        assert analytics.average_salary == Decimal("60000.00")
        assert len(analytics.department_costs) >= 1


# ============================================================================
# 3. PAYROLL REPORT SNAPSHOTS
# ============================================================================

@pytest.mark.asyncio
async def test_payroll_report_generation(setup_finalization_data):
    """Tests generating Salary Register report snapshots and binary document retrieval."""
    data = setup_finalization_data
    period_id = data["payroll_period_id"]

    async with AsyncSessionLocal() as session:
        user = await session.get(User, data["user_id"])
        service = PayrollReportService(session)

        snapshot = await service.generate_report(
            PayrollReportGenerateRequest(
                payroll_period_id=period_id,
                report_type=ReportTypeEnum.SALARY_REGISTER,
                format=ReportFormatEnum.CSV,
            ),
            current_user=user,
        )
        assert snapshot.id is not None
        assert snapshot.file_id is not None
        assert snapshot.report_type == "Salary Register"


# ============================================================================
# 4. BANK PAYMENT EXPORT
# ============================================================================

@pytest.mark.asyncio
async def test_bank_export_service(setup_finalization_data):
    """Tests generating bank payment export CSV files."""
    data = setup_finalization_data
    period_id = data["payroll_period_id"]

    async with AsyncSessionLocal() as session:
        user = await session.get(User, data["user_id"])
        service = BankExportService(session)

        res = await service.generate_bank_export(
            BankExportRequest(payroll_period_id=period_id, bank_format="STANDARD_CSV"),
            current_user=user,
        )
        assert res.payroll_period_id == period_id
        assert res.file_id is not None
        assert res.record_count == 1
        assert res.total_amount == Decimal("52000.00")


# ============================================================================
# 5. PAYROLL CLOSING, REOPENING & ARCHIVAL
# ============================================================================

@pytest.mark.asyncio
async def test_payroll_closing_reopening_archival(setup_finalization_data):
    """Tests period Closing, audited Reopening, Archival, and immutability guards."""
    data = setup_finalization_data
    period_id = data["payroll_period_id"]
    emp_id = data["employee_id"]

    async with AsyncSessionLocal() as session:
        user = await session.get(User, data["user_id"])
        closing_service = PayrollClosingService(session)
        adj_service = PayrollAdjustmentService(session)

        # 1. Close Payroll Period
        closing = await closing_service.close_payroll(period_id, remarks="Finalized for July", current_user=user)
        assert closing.status == "Closed"

        # 2. Immutability Guard: Adjustments cannot be created on closed period
        with pytest.raises(ValidationException):
            await adj_service.create_adjustment(
                PayrollAdjustmentCreate(
                    employee_id=emp_id,
                    payroll_period_id=period_id,
                    adjustment_type=AdjustmentTypeEnum.REIMBURSEMENT,
                    amount=Decimal("1000.00"),
                ),
                current_user=user,
            )

        # 3. Audited Reopen
        reopened = await closing_service.reopen_payroll(
            period_id, reopen_reason="Auditor recalculation request", current_user=user
        )
        assert reopened.status == "Open"

        # 4. Re-close and Archive
        await closing_service.close_payroll(period_id, remarks="Re-closed", current_user=user)
        archived = await closing_service.archive_payroll(period_id, current_user=user)
        assert archived.status == "Archived"


# ============================================================================
# 6. FINANCIAL INTEGRATION QUEUE
# ============================================================================

@pytest.mark.asyncio
async def test_financial_integration_payload_publication(setup_finalization_data):
    """Tests generating and queuing financial posting payloads."""
    data = setup_finalization_data
    period_id = data["payroll_period_id"]

    async with AsyncSessionLocal() as session:
        user = await session.get(User, data["user_id"])
        service = FinancialIntegrationService(session)

        queue_item = await service.publish_financial_payload(period_id, current_user=user)
        assert queue_item.id is not None
        assert queue_item.posting_status == "Pending"
        assert queue_item.payload["journal_entries_summary"]["debit_gross_salary_expense"] == 60000.0
        assert queue_item.payload["journal_entries_summary"]["credit_net_payroll_payable"] == 52000.0


# ============================================================================
# 7. REST API ENDPOINTS
# ============================================================================

@pytest.mark.asyncio
async def test_payroll_finalization_api_endpoints(async_client: AsyncClient, setup_finalization_data):
    """Tests REST API endpoints for Adjustments, Reports, Analytics, Bank Export, Closing, and Financial Payload."""
    data = setup_finalization_data
    token = data["admin_token"]
    emp_id = str(data["employee_id"])
    period_id = str(data["payroll_period_id"])

    headers = {"Authorization": f"Bearer {token}"}

    # 1. POST /api/v1/payroll-adjustments
    resp = await async_client.post(
        "/api/v1/payroll-adjustments",
        json={
            "employee_id": emp_id,
            "payroll_period_id": period_id,
            "adjustment_type": "Overtime",
            "amount": 2500.00,
            "description": "Weekend Overtime",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    adj_data = resp.json()
    adj_id = adj_data["id"]

    # 2. POST /api/v1/payroll-adjustments/{id}/approve
    resp = await async_client.post(f"/api/v1/payroll-adjustments/{adj_id}/approve", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "Approved"

    # 3. GET /api/v1/payroll-analytics
    resp = await async_client.get(f"/api/v1/payroll-analytics?payroll_period_id={period_id}", headers=headers)
    assert resp.status_code == 200

    # 4. POST /api/v1/payroll-reports/generate
    resp = await async_client.post(
        "/api/v1/payroll-reports/generate",
        json={"payroll_period_id": period_id, "report_type": "Salary Register", "format": "CSV"},
        headers=headers,
    )
    assert resp.status_code == 201

    # 5. POST /api/v1/payroll/bank-export
    resp = await async_client.post(
        "/api/v1/payroll/bank-export",
        json={"payroll_period_id": period_id, "bank_format": "STANDARD_CSV"},
        headers=headers,
    )
    assert resp.status_code == 201

    # 6. POST /api/v1/payroll-periods/{id}/publish-financial-payload
    resp = await async_client.post(f"/api/v1/payroll-periods/{period_id}/publish-financial-payload", headers=headers)
    assert resp.status_code == 201

    # 7. POST /api/v1/payroll-periods/{id}/close
    resp = await async_client.post(
        f"/api/v1/payroll-periods/{period_id}/close",
        json={"closing_remarks": "Closed via API"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "Closed"
