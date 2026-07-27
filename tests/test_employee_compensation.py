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
from app.models.salary_structure import SalaryStructure
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.employee_compensation import (
    EmployeeCompensationCreate,
    EmployeeCompensationRevise,
)
from app.schemas.salary_structure import SalaryStructureCreate
from app.services.employee_compensation import EmployeeCompensationService
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
async def setup_compensation_fixture(db_session: AsyncSession):
    """
    Creates test Roles, Users, Employees, Permissions, and Salary Structures for testing Employee Compensation.
    """
    perms = [
        "compensation.create", "compensation.read",
        "compensation.update", "compensation.activate", "compensation.cancel", "compensation.delete",
        "salary_structure.create", "salary_structure.read"
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

    role_admin = Role(name=f"PayrollAdmin_{uuid.uuid4().hex[:6]}", description="Payroll Admin Role")
    db_session.add(role_admin)
    await db_session.flush()

    for p_obj in perm_objs.values():
        db_session.add(RolePermission(role_id=role_admin.id, permission_id=p_obj.id))

    user_admin = User(
        full_name="Payroll Admin",
        username=f"padmin_{uuid.uuid4().hex[:6]}",
        email=f"padmin_{uuid.uuid4().hex[:6]}@example.com",
        password_hash=hash_password("password123"),
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user_admin)
    await db_session.flush()

    db_session.add(UserRole(user_id=user_admin.id, role_id=role_admin.id))

    dept = Department(name=f"Payroll Dept {uuid.uuid4().hex[:4]}", code=f"PR_{uuid.uuid4().hex[:4].upper()}")
    db_session.add(dept)
    await db_session.flush()

    emp_user = User(
        full_name="John Payroll Doe",
        username=f"jdoe_{uuid.uuid4().hex[:6]}",
        email=f"jdoe_{uuid.uuid4().hex[:6]}@example.com",
        password_hash=hash_password("password123"),
        is_active=True,
    )
    db_session.add(emp_user)
    await db_session.flush()

    employee = Employee(
        user_id=emp_user.id,
        department_id=dept.id,
        employee_code=f"EMP_{uuid.uuid4().hex[:4].upper()}",
        first_name="John",
        last_name="Doe",
        work_email=emp_user.email,
        joining_date=datetime.date(2025, 1, 1),
    )
    db_session.add(employee)
    await db_session.commit()
    await db_session.refresh(user_admin)
    await db_session.refresh(employee)

    # Create dummy salary structure
    struct_service = SalaryStructureService(db_session)
    struct = await struct_service.create_structure(
        SalaryStructureCreate(
            code=f"EXEC_{uuid.uuid4().hex[:4].upper()}",
            name=f"Executive Structure {uuid.uuid4().hex[:4]}",
            currency="INR",
            is_active=True,
            effective_from=datetime.date(2026, 1, 1),
        ),
        current_user=user_admin,
    )

    return {
        "role_admin": role_admin,
        "user_admin": user_admin,
        "employee": employee,
        "structure": struct,
    }


@pytest.mark.asyncio
async def test_employee_compensation_lifecycle(db_session: AsyncSession, setup_compensation_fixture):
    """
    Tests full lifecycle of Employee Compensation: assign, activate, revise, auto-expire previous, date overlap.
    """
    fix = setup_compensation_fixture
    service = EmployeeCompensationService(db_session)

    assign_dto = EmployeeCompensationCreate(
        employee_id=fix["employee"].id,
        salary_structure_id=fix["structure"].id,
        effective_from=datetime.date(2026, 1, 1),
        effective_to=None,
        annual_ctc=1200000.00,
        monthly_gross_salary=100000.00,
        remarks="Initial Compensation Assignment",
    )

    # 1. Assign Compensation (Draft status)
    comp1 = await service.assign_compensation(data=assign_dto, current_user=fix["user_admin"])
    assert comp1.id is not None
    assert comp1.status == "Draft"
    assert comp1.revision_number == 1

    # 2. Activate Compensation
    active1 = await service.activate_compensation(id=comp1.id, current_user=fix["user_admin"])
    assert active1.status == "Active"
    assert active1.approved_by == fix["user_admin"].id

    # 3. Revise Compensation (creates new revision)
    revise_dto = EmployeeCompensationRevise(
        salary_structure_id=fix["structure"].id,
        effective_from=datetime.date(2026, 7, 1),
        effective_to=None,
        annual_ctc=1440000.00,
        monthly_gross_salary=120000.00,
        remarks="Mid-Year Merit Revision",
    )
    comp2 = await service.revise_compensation(
        previous_id=active1.id, data=revise_dto, current_user=fix["user_admin"]
    )
    assert comp2.id is not None
    assert comp2.status == "Draft"
    assert comp2.revision_number == 2
    assert comp2.previous_compensation_id == active1.id

    # 4. Activate Revision (auto-expires comp1)
    active2 = await service.activate_compensation(id=comp2.id, current_user=fix["user_admin"])
    assert active2.status == "Active"

    # Re-fetch active1 to verify auto-expiration
    refreshed_active1 = await service.get_compensation_by_id(active1.id)
    assert refreshed_active1.status == "Expired"
    assert refreshed_active1.effective_to == datetime.date(2026, 6, 30)

    # 5. Overlapping Date Validation Rejection
    overlap_dto = EmployeeCompensationCreate(
        employee_id=fix["employee"].id,
        salary_structure_id=fix["structure"].id,
        effective_from=datetime.date(2026, 8, 1),
        effective_to=datetime.date(2026, 10, 1),
        annual_ctc=1500000.00,
        monthly_gross_salary=125000.00,
    )
    with pytest.raises(ApnaERPException) as exc_info:
        await service.assign_compensation(data=overlap_dto, current_user=fix["user_admin"])
    assert exc_info.value.error_code == "OVERLAPPING_COMPENSATION_DATES"


@pytest.mark.asyncio
async def test_employee_compensation_api_endpoints(async_client: AsyncClient, db_session: AsyncSession, setup_compensation_fixture):
    """
    Tests REST API endpoints for Employee Compensation.
    """
    fix = setup_compensation_fixture
    token = create_access_token(subject=str(fix["user_admin"].id))
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "employee_id": str(fix["employee"].id),
        "salary_structure_id": str(fix["structure"].id),
        "effective_from": "2026-01-01",
        "annual_ctc": 900000.00,
        "monthly_gross_salary": 75000.00,
        "remarks": "Standard Offer Package",
    }

    # 1. POST /api/v1/employee-compensations
    res_create = await async_client.post("/api/v1/employee-compensations", json=payload, headers=headers)
    assert res_create.status_code == 201
    body_create = res_create.json()
    assert body_create["status"] == "Draft"
    comp_id = body_create["id"]

    # 2. POST /api/v1/employee-compensations/{id}/activate
    res_act = await async_client.post(f"/api/v1/employee-compensations/{comp_id}/activate", headers=headers)
    assert res_act.status_code == 200
    assert res_act.json()["status"] == "Active"

    # 3. GET /api/v1/employees/{id}/compensation
    res_curr = await async_client.get(f"/api/v1/employees/{fix['employee'].id}/compensation", headers=headers)
    assert res_curr.status_code == 200
    assert res_curr.json()["id"] == comp_id

    # 4. GET /api/v1/employees/{id}/compensation/history
    res_hist = await async_client.get(f"/api/v1/employees/{fix['employee'].id}/compensation/history", headers=headers)
    assert res_hist.status_code == 200
    assert len(res_hist.json()) >= 1

    # 5. POST /api/v1/employee-compensations/{id}/cancel
    res_cancel = await async_client.post(f"/api/v1/employee-compensations/{comp_id}/cancel", headers=headers)
    assert res_cancel.status_code == 200
    assert res_cancel.json()["status"] == "Cancelled"

    # 6. DELETE /api/v1/employee-compensations/{id}
    res_del = await async_client.delete(f"/api/v1/employee-compensations/{comp_id}", headers=headers)
    assert res_del.status_code == 204
