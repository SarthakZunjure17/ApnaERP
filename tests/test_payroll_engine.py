from unittest.mock import patch
import datetime
from typing import AsyncGenerator
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.db.session import AsyncSessionLocal
from app.exceptions.base import ApnaERPException
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
from app.schemas.salary_structure import SalaryStructureCreate
from app.services.employee_compensation import EmployeeCompensationService
from app.services.payroll_engine import PayrollEngineService
from app.services.salary_component import SalaryComponentService
from app.services.salary_structure import SalaryStructureService


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
async def setup_payroll_engine_fixture(db_session: AsyncSession):
    """
    Sets up Roles, Users, Employees, Permissions, Salary Components, Salary Structures, and Compensation for Payroll Engine testing.
    """
    perms = [
        "payroll.generate", "payroll.read", "payroll.approve", "payroll.lock",
        "compensation.create", "compensation.activate",
        "salary_structure.create", "salary_component.create",
    ]
    perm_objs = {}
    for p_code in perms:
        stmt = select(Permission).where(Permission.code == p_code)
        res = await db_session.execute(stmt)
        p_obj = res.scalars().first()
        if not p_obj:
            p_obj = Permission(name=p_code.replace(".", " ").title(), code=p_code, module_name="payroll")
            db_session.add(p_obj)
            await db_session.flush()
        perm_objs[p_code] = p_obj

    role_admin = Role(name=f"PayrollEngineAdmin_{uuid.uuid4().hex[:6]}", description="Payroll Engine Admin Role")
    db_session.add(role_admin)
    await db_session.flush()

    for p_obj in perm_objs.values():
        db_session.add(RolePermission(role_id=role_admin.id, permission_id=p_obj.id))

    user_admin = User(
        full_name="Payroll Engine Admin",
        username=f"peadmin_{uuid.uuid4().hex[:6]}",
        email=f"peadmin_{uuid.uuid4().hex[:6]}@example.com",
        password_hash=hash_password("password123"),
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user_admin)
    await db_session.flush()

    db_session.add(UserRole(user_id=user_admin.id, role_id=role_admin.id))

    dept = Department(name=f"Payroll Engine Dept {uuid.uuid4().hex[:4]}", code=f"PE_{uuid.uuid4().hex[:4].upper()}")
    db_session.add(dept)
    await db_session.flush()

    emp_user = User(
        full_name="Alice Payroll Worker",
        username=f"aworker_{uuid.uuid4().hex[:6]}",
        email=f"aworker_{uuid.uuid4().hex[:6]}@example.com",
        password_hash=hash_password("password123"),
        is_active=True,
    )
    db_session.add(emp_user)
    await db_session.flush()

    employee = Employee(
        user_id=emp_user.id,
        department_id=dept.id,
        employee_code=f"EMP_{uuid.uuid4().hex[:4].upper()}",
        first_name="Alice",
        last_name="Worker",
        work_email=emp_user.email,
        joining_date=datetime.date(2025, 1, 1),
    )
    db_session.add(employee)
    await db_session.commit()
    await db_session.refresh(user_admin)
    await db_session.refresh(employee)

    # 1. Salary Components (Basic Earning + PF Deduction)
    import random
    basic_comp = SalaryComponent(
        code=f"BASIC_{uuid.uuid4().hex[:4].upper()}",
        name=f"Basic Salary {uuid.uuid4().hex[:4]}",
        type="Earning",
        calculation_method="Percentage",
        percentage_value=50.00,
        is_taxable=True,
        is_active=True,
        display_order=random.randint(10000, 999999),
    )
    pf_comp = SalaryComponent(
        code=f"PF_{uuid.uuid4().hex[:4].upper()}",
        name=f"Provident Fund {uuid.uuid4().hex[:4]}",
        type="Deduction",
        calculation_method="Fixed",
        default_value=1800.00,
        is_active=True,
        display_order=random.randint(10000, 999999),
    )
    db_session.add(basic_comp)
    db_session.add(pf_comp)
    await db_session.flush()

    # 2. Salary Structure
    struct_service = SalaryStructureService(db_session)
    struct = await struct_service.create_structure(
        SalaryStructureCreate(
            code=f"ENG_STRUCT_{uuid.uuid4().hex[:4].upper()}",
            name=f"Engineering Structure {uuid.uuid4().hex[:4]}",
            currency="INR",
            is_active=True,
            effective_from=datetime.date(2026, 1, 1),
        ),
        current_user=user_admin,
    )

    # Add components to structure
    sc1 = SalaryStructureComponent(salary_structure_id=struct.id, salary_component_id=basic_comp.id, component_order=1, component_value=60000.00)
    sc2 = SalaryStructureComponent(salary_structure_id=struct.id, salary_component_id=pf_comp.id, component_order=2, component_value=1800.00)
    sc1.component = basic_comp
    sc2.component = pf_comp
    struct.components = [sc1, sc2]
    db_session.add_all([sc1, sc2])
    await db_session.commit()

    # 3. Employee Compensation (Active)
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

    return {
        "user_admin": user_admin,
        "employee": employee,
        "structure": struct,
        "compensation": comp,
    }


@pytest.mark.asyncio
@patch("app.services.payroll_engine.send_payroll_notification_task")
async def test_payroll_engine_lifecycle(mock_notify, db_session: AsyncSession, setup_payroll_engine_fixture):
    """
    Tests full lifecycle of Payroll Processing Engine: create period, generate, approve, lock, lock constraint.
    """
    fix = setup_payroll_engine_fixture
    service = PayrollEngineService(db_session)

    # 1. Create Payroll Period
    period_dto = PayrollPeriodCreate(
        period_code=f"2026-01_{uuid.uuid4().hex[:4]}",
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 1, 31),
    )
    period = await service.create_payroll_period(data=period_dto, current_user=fix["user_admin"])
    assert period.id is not None
    assert period.status == "Draft"

    # 2. Generate Payroll
    records = await service.generate_payroll(period_id=period.id, current_user=fix["user_admin"])
    assert len(records) >= 1
    rec = next((r for r in records if str(r.employee_id) == str(fix["employee"].id)), None)
    assert rec is not None, f"Payroll record for test employee '{fix['employee'].id}' not found in generated records"
    assert str(rec.employee_id) == str(fix["employee"].id)
    assert rec.gross_salary > 0
    assert rec.net_salary > 0
    assert rec.net_salary <= rec.gross_salary
    assert len(rec.components) >= 2

    # Verify period status updated to Completed
    period_refreshed = await service.period_repository.get_by_id(db_session, period.id)
    assert period_refreshed.status == "Completed"

    # 3. Approve Payroll
    approved_period = await service.approve_payroll(period_id=period.id, current_user=fix["user_admin"])
    assert approved_period.status == "Completed"

    refreshed_rec = await service.get_payroll_record_by_id(rec.id)
    assert refreshed_rec.status == "Approved"

    # 4. Lock Payroll Period
    locked_period = await service.lock_payroll_period(period_id=period.id, current_user=fix["user_admin"])
    assert locked_period.status == "Locked"

    # 5. Verify Locked Period Rejection on Regeneration
    with pytest.raises(ApnaERPException) as exc_info:
        await service.generate_payroll(period_id=period.id, current_user=fix["user_admin"])
    assert exc_info.value.error_code == "PERIOD_LOCKED"


@pytest.mark.asyncio
@patch("app.services.payroll_engine.send_payroll_notification_task")
async def test_payroll_engine_api_endpoints(mock_notify, async_client: AsyncClient, db_session: AsyncSession, setup_payroll_engine_fixture):
    """
    Tests REST API endpoints for Payroll Processing Engine.
    """
    fix = setup_payroll_engine_fixture
    token = create_access_token(subject=str(fix["user_admin"].id))
    headers = {"Authorization": f"Bearer {token}"}

    period_code = f"2026-02_{uuid.uuid4().hex[:4]}"
    payload = {
        "period_code": period_code,
        "start_date": "2026-02-01",
        "end_date": "2026-02-28",
    }

    # 1. POST /api/v1/payroll-periods
    res_create = await async_client.post("/api/v1/payroll-periods", json=payload, headers=headers)
    assert res_create.status_code == 201
    period_id = res_create.json()["id"]

    # 2. POST /api/v1/payroll-periods/{id}/generate
    res_gen = await async_client.post(f"/api/v1/payroll-periods/{period_id}/generate", headers=headers)
    assert res_gen.status_code == 200
    records = res_gen.json()
    assert len(records) >= 1
    rec_id = records[0]["id"]

    # 3. GET /api/v1/payroll-records/{id}
    res_rec = await async_client.get(f"/api/v1/payroll-records/{rec_id}", headers=headers)
    assert res_rec.status_code == 200
    assert res_rec.json()["id"] == rec_id

    # 4. GET /api/v1/employees/{id}/payroll
    res_emp_hist = await async_client.get(f"/api/v1/employees/{fix['employee'].id}/payroll", headers=headers)
    assert res_emp_hist.status_code == 200
    assert len(res_emp_hist.json()) >= 1

    # 5. POST /api/v1/payroll-periods/{id}/approve
    res_app = await async_client.post(f"/api/v1/payroll-periods/{period_id}/approve", headers=headers)
    assert res_app.status_code == 200

    # 6. POST /api/v1/payroll-periods/{id}/lock
    res_lock = await async_client.post(f"/api/v1/payroll-periods/{period_id}/lock", headers=headers)
    assert res_lock.status_code == 200
    assert res_lock.json()["status"] == "Locked"
