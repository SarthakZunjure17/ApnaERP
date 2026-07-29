from unittest.mock import patch
import datetime
import random
from typing import AsyncGenerator
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.db.session import AsyncSessionLocal
from app.exceptions.base import ApnaERPException, DuplicateResourceException
from app.main import app
from app.models.department import Department
from app.models.employee import Employee
from app.models.permission import Permission
from app.models.role import Role, RolePermission
from app.models.salary_component import SalaryComponent
from app.models.salary_structure import SalaryStructure, SalaryStructureComponent
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.employee_compensation import EmployeeCompensationCreate
from app.schemas.payroll_period import PayrollPeriodCreate
from app.schemas.payroll_run import PayrollRunCreate
from app.schemas.salary_structure import SalaryStructureCreate
from app.services.employee_compensation import EmployeeCompensationService
from app.services.payroll_engine import PayrollEngineService
from app.services.payroll_run import PayrollRunService
from app.services.salary_structure import SalaryStructureService
from app.utils.pdf_generator import generate_payslip_pdf_bytes


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
async def setup_payroll_run_fixture(db_session: AsyncSession):
    """
    Sets up users, employee, salary components, structure, active compensation, and payroll period.
    """
    # Role & Permissions setup
    perms_query = await db_session.execute(Permission.__table__.select())
    all_perms = perms_query.fetchall()

    role = Role(
        name=f"PayrollRunAdmin_{uuid.uuid4().hex[:6]}",
        description="Payroll Run Admin Role",
    )
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)

    for p in all_perms:
        db_session.add(RolePermission(role_id=role.id, permission_id=p.id))
    await db_session.commit()

    user_admin = User(
        full_name="Payroll Run Admin",
        email=f"pradmin_{uuid.uuid4().hex[:6]}@example.com",
        username=f"pradmin_{uuid.uuid4().hex[:6]}",
        password_hash=hash_password("Pass123!"),
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user_admin)
    await db_session.commit()
    await db_session.refresh(user_admin)

    db_session.add(UserRole(user_id=user_admin.id, role_id=role.id))
    await db_session.commit()

    # Department & Employee
    dept = Department(
        code=f"PR_{uuid.uuid4().hex[:4].upper()}",
        name=f"Payroll Dept {uuid.uuid4().hex[:4]}",
        is_active=True,
    )
    db_session.add(dept)
    await db_session.commit()
    await db_session.refresh(dept)

    emp_user = User(
        full_name="Bob Payroll Worker",
        email=f"bworker_{uuid.uuid4().hex[:6]}@example.com",
        username=f"bworker_{uuid.uuid4().hex[:6]}",
        password_hash=hash_password("Pass123!"),
        is_active=True,
    )
    db_session.add(emp_user)
    await db_session.commit()
    await db_session.refresh(emp_user)

    employee = Employee(
        employee_code=f"EMP_{uuid.uuid4().hex[:4].upper()}",
        first_name="Bob",
        last_name="Worker",
        work_email=emp_user.email,
        user_id=emp_user.id,
        department_id=dept.id,
        employment_type="Full Time",
        employment_status="Active",
        joining_date=datetime.date(2025, 1, 1),
        is_active=True,
    )
    db_session.add(employee)
    await db_session.commit()
    await db_session.refresh(employee)

    # Salary Components & Structure
    order_1 = random.randint(10000, 90000)
    order_2 = random.randint(90001, 99999)

    basic_comp = SalaryComponent(
        code=f"BASIC_{uuid.uuid4().hex[:4].upper()}",
        name=f"Basic Salary {uuid.uuid4().hex[:4]}",
        type="Earning",
        calculation_method="Percentage",
        percentage_value=50.00,
        is_taxable=True,
        is_active=True,
        display_order=order_1,
    )
    pf_comp = SalaryComponent(
        code=f"PF_{uuid.uuid4().hex[:4].upper()}",
        name=f"Provident Fund {uuid.uuid4().hex[:4]}",
        type="Deduction",
        calculation_method="Fixed",
        default_value=1800.00,
        is_active=True,
        display_order=order_2,
    )
    db_session.add_all([basic_comp, pf_comp])
    await db_session.commit()

    struct_service = SalaryStructureService(db_session)
    struct = await struct_service.create_structure(
        SalaryStructureCreate(
            code=f"PR_STRUCT_{uuid.uuid4().hex[:4].upper()}",
            name=f"Payroll Structure {uuid.uuid4().hex[:4]}",
            currency="INR",
            is_active=True,
            effective_from=datetime.date(2026, 1, 1),
        ),
        current_user=user_admin,
    )

    sc1 = SalaryStructureComponent(salary_structure_id=struct.id, salary_component_id=basic_comp.id, component_order=1, component_value=60000.00)
    sc2 = SalaryStructureComponent(salary_structure_id=struct.id, salary_component_id=pf_comp.id, component_order=2, component_value=1800.00)
    sc1.component = basic_comp
    sc2.component = pf_comp
    struct.components = [sc1, sc2]
    db_session.add_all([sc1, sc2])
    await db_session.commit()

    comp_service = EmployeeCompensationService(db_session)
    comp_draft = await comp_service.assign_compensation(
        EmployeeCompensationCreate(
            employee_id=employee.id,
            salary_structure_id=struct.id,
            effective_from=datetime.date(2026, 1, 1),
            annual_ctc=1440000.00,
            monthly_gross_salary=120000.00,
            remarks="Standard Tech Package",
        ),
        current_user=user_admin,
    )
    comp = await comp_service.activate_compensation(id=comp_draft.id, current_user=user_admin)

    # Create Payroll Period
    payroll_engine_service = PayrollEngineService(db_session)
    period = await payroll_engine_service.create_payroll_period(
        data=PayrollPeriodCreate(
            period_code=f"2026-03_{uuid.uuid4().hex[:4]}",
            start_date=datetime.date(2026, 3, 1),
            end_date=datetime.date(2026, 3, 31),
        ),
        current_user=user_admin,
    )

    return {
        "user_admin": user_admin,
        "emp_user": emp_user,
        "employee": employee,
        "period": period,
    }


def test_pdf_payslip_generation():
    """
    Tests ReportLab PDF generator function produces valid binary PDF content.
    """
    pdf_bytes = generate_payslip_pdf_bytes(
        payslip_number="PS-202603-TEST01",
        employee_code="EMP_TEST",
        employee_name="John Doe",
        department_name="Engineering",
        work_email="johndoe@example.com",
        period_code="2026-03",
        period_start=datetime.date(2026, 3, 1),
        period_end=datetime.date(2026, 3, 31),
        gross_salary=120000.00,
        total_earnings=60000.00,
        total_deductions=1800.00,
        net_salary=58200.00,
        components=[
            {"name": "Basic Salary", "type": "Earning", "amount": 60000.00},
            {"name": "Provident Fund", "type": "Deduction", "amount": 1800.00},
        ],
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")


@pytest.mark.asyncio
@patch("app.services.payroll_run.send_payroll_run_notification_task")
@patch("app.services.payroll_run.send_payslip_published_notification_task")
async def test_payroll_run_lifecycle(mock_pub_task, mock_run_task, db_session: AsyncSession, setup_payroll_run_fixture):
    """
    Tests PayrollRun lifecycle: create, start, complete, lock, and duplicate constraint checks.
    """
    fix = setup_payroll_run_fixture
    service = PayrollRunService(db_session)

    # 1. Create Payroll Run
    run = await service.create_payroll_run(
        data=PayrollRunCreate(
            payroll_period_id=fix["period"].id,
            run_type="Regular",
            remarks="March 2026 Regular Run",
        ),
        current_user=fix["user_admin"],
    )
    assert run.id is not None
    assert run.status == "Draft"
    assert run.run_number.startswith(f"RUN-{fix['period'].period_code}")

    # Verify duplicate run_type constraint
    with pytest.raises(DuplicateResourceException):
        await service.create_payroll_run(
            data=PayrollRunCreate(
                payroll_period_id=fix["period"].id,
                run_type="Regular",
            ),
            current_user=fix["user_admin"],
        )

    # 2. Start Run
    run_started = await service.start_payroll_run(run_id=run.id, current_user=fix["user_admin"])
    assert run_started.status == "Processing"
    assert run_started.started_at is not None

    # 3. Complete Run
    run_completed = await service.complete_payroll_run(run_id=run.id, current_user=fix["user_admin"])
    assert run_completed.status == "Completed"
    assert run_completed.completed_at is not None

    # 4. Lock Run
    run_locked = await service.lock_payroll_run(run_id=run.id, current_user=fix["user_admin"])
    assert run_locked.status == "Locked"
    assert run_locked.locked_at is not None

    # Verify locked run modification rejection
    with pytest.raises(ApnaERPException) as exc_info:
        await service.start_payroll_run(run_id=run.id, current_user=fix["user_admin"])
    assert exc_info.value.error_code == "RUN_LOCKED"


@pytest.mark.asyncio
@patch("app.services.payroll_engine.send_payroll_notification_task")
@patch("app.services.payroll_run.send_payroll_run_notification_task")
@patch("app.services.payroll_run.send_payslip_published_notification_task")
async def test_payslip_generation_and_publishing(
    mock_pub_task, mock_run_task, mock_engine_task, db_session: AsyncSession, setup_payroll_run_fixture
):
    """
    Tests generating payroll, creating a run, generating PDF payslips, and publishing.
    """
    fix = setup_payroll_run_fixture
    engine_service = PayrollEngineService(db_session)
    run_service = PayrollRunService(db_session)

    # 1. Generate Payroll for period
    records = await engine_service.generate_payroll(period_id=fix["period"].id, current_user=fix["user_admin"])
    assert len(records) >= 1

    # 2. Create Payroll Run
    run = await run_service.create_payroll_run(
        data=PayrollRunCreate(
            payroll_period_id=fix["period"].id,
            run_type="Regular",
        ),
        current_user=fix["user_admin"],
    )

    # 3. Generate Payslips
    payslips = await run_service.generate_payslips(run_id=run.id, current_user=fix["user_admin"])
    assert len(payslips) >= 1

    emp_payslip = next((p for p in payslips if str(p.employee_id) == str(fix["employee"].id)), payslips[0])
    assert emp_payslip.status == "Generated"
    assert emp_payslip.pdf_file_id is not None
    assert emp_payslip.generated_at is not None

    # 4. Publish Payslips
    published_payslips = await run_service.publish_payslips(run_id=run.id, current_user=fix["user_admin"])
    assert len(published_payslips) >= 1
    assert published_payslips[0].status == "Published"
    assert published_payslips[0].published_at is not None


@pytest.mark.asyncio
@patch("app.services.payroll_engine.send_payroll_notification_task")
@patch("app.services.payroll_run.send_payroll_run_notification_task")
@patch("app.services.payroll_run.send_payslip_published_notification_task")
async def test_payroll_run_and_payslip_api_endpoints(
    mock_pub_task, mock_run_task, mock_engine_task, async_client: AsyncClient, db_session: AsyncSession, setup_payroll_run_fixture
):
    """
    Tests REST API endpoints for Payroll Runs and Payslips.
    """
    fix = setup_payroll_run_fixture
    token = create_access_token(subject=str(fix["user_admin"].id))
    headers = {"Authorization": f"Bearer {token}"}

    # Generate Payroll first
    engine_service = PayrollEngineService(db_session)
    await engine_service.generate_payroll(period_id=fix["period"].id, current_user=fix["user_admin"])

    # 1. POST /api/v1/payroll-runs
    run_payload = {
        "payroll_period_id": str(fix["period"].id),
        "run_type": "Regular",
        "remarks": "API Run Test",
    }
    res_create = await async_client.post("/api/v1/payroll-runs", json=run_payload, headers=headers)
    assert res_create.status_code == 201
    run_id = res_create.json()["id"]

    # 2. GET /api/v1/payroll-runs/{id}
    res_get = await async_client.get(f"/api/v1/payroll-runs/{run_id}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["id"] == run_id

    # 3. POST /api/v1/payroll-runs/{id}/start
    res_start = await async_client.post(f"/api/v1/payroll-runs/{run_id}/start", headers=headers)
    assert res_start.status_code == 200
    assert res_start.json()["status"] == "Processing"

    # 4. POST /api/v1/payroll-runs/{id}/generate-payslips
    res_gen_ps = await async_client.post(f"/api/v1/payroll-runs/{run_id}/generate-payslips", headers=headers)
    assert res_gen_ps.status_code == 200
    ps_data = res_gen_ps.json()
    assert len(ps_data) >= 1
    payslip_id = ps_data[0]["id"]

    # 5. POST /api/v1/payroll-runs/{id}/publish-payslips
    res_pub_ps = await async_client.post(f"/api/v1/payroll-runs/{run_id}/publish-payslips", headers=headers)
    assert res_pub_ps.status_code == 200

    # 6. GET /api/v1/payslips/{id}
    res_ps = await async_client.get(f"/api/v1/payslips/{payslip_id}", headers=headers)
    assert res_ps.status_code == 200
    assert res_ps.json()["id"] == payslip_id

    # 7. GET /api/v1/employees/{id}/payslips
    res_emp_ps = await async_client.get(f"/api/v1/employees/{fix['employee'].id}/payslips", headers=headers)
    assert res_emp_ps.status_code == 200
    assert len(res_emp_ps.json()) >= 1

    # 8. GET /api/v1/payslips/{id}/download
    res_dl = await async_client.get(f"/api/v1/payslips/{payslip_id}/download", headers=headers)
    assert res_dl.status_code == 200
    assert res_dl.headers["content-type"] == "application/pdf"
    assert res_dl.content.startswith(b"%PDF")
