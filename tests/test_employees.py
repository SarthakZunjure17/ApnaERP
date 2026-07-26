import datetime
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.core.celery import celery_app
from app.db.session import AsyncSessionLocal
from app.models.department import Department
from app.models.employee import Employee
from app.models.user import User
from app.repositories.department import department_repository
from app.repositories.employee import employee_repository
from app.repositories.user import user_repository
from app.schemas.employee import EmployeeCreate, EmployeeUpdate, EmploymentStatus, EmploymentType
from app.services.employee import EmployeeService


@pytest_asyncio.fixture
async def admin_token(async_client: AsyncClient) -> str:
    """
    Fixture creating a Super Admin user and returning Bearer authorization token.
    """
    unique_id = uuid.uuid4().hex[:6]
    email = f"empadmin_{unique_id}@example.com"
    username = f"empadmin_{unique_id}"

    reg_payload = {
        "full_name": "Employee Admin",
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


@pytest_asyncio.fixture
async def test_department() -> Department:
    """
    Fixture creating an active department for employee testing.
    """
    async with AsyncSessionLocal() as session:
        code = f"DEPT-EMP-{uuid.uuid4().hex[:6]}"
        name = f"Dept for Employees {uuid.uuid4().hex[:6]}"
        dept = await department_repository.create(session, obj_in={
            "code": code,
            "name": name,
            "description": "Active Department for Employee Tests",
            "is_active": True,
        })
        return dept


@pytest.mark.asyncio
async def test_employee_repository_crud(test_department: Department):
    """
    Tests direct EmployeeRepository database operations.
    """
    async with AsyncSessionLocal() as session:
        repo = employee_repository
        code = f"EMP-REPO-{uuid.uuid4().hex[:6]}"
        email = f"repo_{uuid.uuid4().hex[:6]}@example.com"

        emp = await repo.create(session, obj_in={
            "employee_code": code,
            "first_name": "John",
            "last_name": "Doe",
            "work_email": email,
            "department_id": test_department.id,
            "employment_type": EmploymentType.FULL_TIME.value,
            "employment_status": EmploymentStatus.ACTIVE.value,
            "joining_date": datetime.date(2026, 1, 15),
            "is_active": True,
        })
        assert emp.id is not None
        assert emp.employee_code == code

        fetched = await repo.get_by_code(session, code)
        assert fetched is not None
        assert fetched.id == emp.id

        by_email = await repo.get_by_work_email(session, email)
        assert by_email is not None
        assert by_email.id == emp.id

        by_dept = await repo.get_by_department(session, test_department.id)
        assert len(by_dept) >= 1

        assert await repo.exists_by_code(session, code) is True
        assert await repo.exists_by_work_email(session, email) is True

        # Soft delete & restore
        await repo.soft_delete(session, id=emp.id)
        assert await repo.get_by_code(session, code) is None

        await repo.restore(session, id=emp.id)
        assert await repo.get_by_code(session, code) is not None


@pytest.mark.asyncio
async def test_employee_service_business_rules(test_department: Department):
    """
    Tests EmployeeService business rules and validations:
    - Unique employee code and work email
    - Invalid dates (joining_date > exit_date)
    - Self-management block
    - Circular manager reporting loop check
    - Inactive department check
    """
    async with AsyncSessionLocal() as session:
        service = EmployeeService(session)
        code1 = f"EMP-SRV1-{uuid.uuid4().hex[:6]}"
        code2 = f"EMP-SRV2-{uuid.uuid4().hex[:6]}"
        email1 = f"srv1_{uuid.uuid4().hex[:6]}@example.com"
        email2 = f"srv2_{uuid.uuid4().hex[:6]}@example.com"

        # 1. Create Manager Employee
        mgr = await service.create_employee(EmployeeCreate(
            employee_code=code1,
            first_name="Alice",
            last_name="Manager",
            work_email=email1,
            department_id=test_department.id,
            joining_date=datetime.date(2025, 1, 1),
        ))

        # 2. Duplicate Code Error
        with pytest.raises(Exception) as exc_info:
            await service.create_employee(EmployeeCreate(
                employee_code=code1,
                first_name="Duplicate",
                last_name="Code",
                work_email=f"dup_{uuid.uuid4().hex[:6]}@example.com",
                department_id=test_department.id,
                joining_date=datetime.date(2025, 1, 1),
            ))
        assert "already exists" in str(exc_info.value)

        # 3. Duplicate Email Error
        with pytest.raises(Exception) as exc_info:
            await service.create_employee(EmployeeCreate(
                employee_code=f"UNIQUE-{uuid.uuid4().hex[:6]}",
                first_name="Duplicate",
                last_name="Email",
                work_email=email1,
                department_id=test_department.id,
                joining_date=datetime.date(2025, 1, 1),
            ))
        assert "already exists" in str(exc_info.value)

        # 4. Invalid Dates Error (joining_date > exit_date)
        with pytest.raises(Exception) as exc_info:
            await service.create_employee(EmployeeCreate(
                employee_code=f"DATES-{uuid.uuid4().hex[:6]}",
                first_name="Invalid",
                last_name="Dates",
                work_email=f"dates_{uuid.uuid4().hex[:6]}@example.com",
                department_id=test_department.id,
                joining_date=datetime.date(2026, 5, 1),
                exit_date=datetime.date(2026, 1, 1),
            ))
        assert "Joining date cannot be after exit date" in str(exc_info.value)

        # 5. Create Subordinate Employee
        sub = await service.create_employee(EmployeeCreate(
            employee_code=code2,
            first_name="Bob",
            last_name="Subordinate",
            work_email=email2,
            department_id=test_department.id,
            manager_id=mgr.id,
            joining_date=datetime.date(2025, 6, 1),
        ))

        # 6. Self Management Error
        with pytest.raises(Exception) as exc_info:
            await service.update_employee(mgr.id, EmployeeUpdate(manager_id=mgr.id))
        assert "cannot manage themselves" in str(exc_info.value)

        # 7. Circular Manager Hierarchy Loop Error (Setting manager's manager to subordinate)
        with pytest.raises(Exception) as exc_info:
            await service.update_employee(mgr.id, EmployeeUpdate(manager_id=sub.id))
        assert "Circular manager reporting hierarchy detected" in str(exc_info.value)

        # 8. Inactive Department Error
        inactive_dept = await department_repository.create(session, obj_in={
            "code": f"INACTIVE-{uuid.uuid4().hex[:6]}",
            "name": f"Inactive Dept {uuid.uuid4().hex[:6]}",
            "is_active": False,
        })
        with pytest.raises(Exception) as exc_info:
            await service.create_employee(EmployeeCreate(
                employee_code=f"INACT-{uuid.uuid4().hex[:6]}",
                first_name="Inactive",
                last_name="DeptTest",
                work_email=f"inact_{uuid.uuid4().hex[:6]}@example.com",
                department_id=inactive_dept.id,
                joining_date=datetime.date(2026, 1, 1),
            ))
        assert "inactive and cannot receive employees" in str(exc_info.value)


@pytest.mark.asyncio
async def test_employee_api_endpoints(async_client: AsyncClient, admin_token: str, test_department: Department):
    """
    Tests full RESTful API workflow for Employee Management:
    - POST /api/v1/employees
    - GET /api/v1/employees/hierarchy
    - GET /api/v1/employees/department/{department_id}
    - GET /api/v1/employees
    - GET /api/v1/employees/{id}
    - PUT /api/v1/employees/{id}
    - DELETE /api/v1/employees/{id}
    - PATCH /api/v1/employees/{id}/restore
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    celery_app.conf.task_always_eager = True

    # 1. Create Manager Employee via API
    mgr_code = f"MGR-API-{uuid.uuid4().hex[:6]}"
    res = await async_client.post(
        "/api/v1/employees",
        json={
            "employee_code": mgr_code,
            "first_name": "Executive",
            "last_name": "Manager",
            "work_email": f"execmgr_{uuid.uuid4().hex[:6]}@example.com",
            "department_id": str(test_department.id),
            "joining_date": "2025-01-01",
            "employment_type": "Full Time",
            "employment_status": "Active",
            "is_active": True,
        },
        headers=headers,
    )
    assert res.status_code == 201
    mgr_data = res.json()
    mgr_id = mgr_data["id"]

    # 2. Create Subordinate Employee via API
    sub_code = f"SUB-API-{uuid.uuid4().hex[:6]}"
    res = await async_client.post(
        "/api/v1/employees",
        json={
            "employee_code": sub_code,
            "first_name": "Staff",
            "last_name": "Member",
            "work_email": f"staff_{uuid.uuid4().hex[:6]}@example.com",
            "department_id": str(test_department.id),
            "manager_id": mgr_id,
            "joining_date": "2025-06-01",
            "employment_type": "Full Time",
            "employment_status": "Active",
            "is_active": True,
        },
        headers=headers,
    )
    assert res.status_code == 201
    sub_data = res.json()
    sub_id = sub_data["id"]

    # 3. GET /api/v1/employees/hierarchy
    res = await async_client.get("/api/v1/employees/hierarchy", headers=headers)
    assert res.status_code == 200
    hierarchy = res.json()
    assert isinstance(hierarchy, list)
    matching_mgrs = [e for e in hierarchy if e["id"] == mgr_id]
    assert len(matching_mgrs) == 1
    assert len(matching_mgrs[0]["direct_reports"]) >= 1

    # 4. GET /api/v1/employees/department/{department_id}
    res = await async_client.get(f"/api/v1/employees/department/{test_department.id}", headers=headers)
    assert res.status_code == 200
    dept_emps = res.json()
    assert len(dept_emps) >= 2

    # 5. GET /api/v1/employees (List with search)
    res = await async_client.get(f"/api/v1/employees?search={mgr_code}", headers=headers)
    assert res.status_code == 200
    list_data = res.json()
    assert list_data["total"] >= 1

    # 6. GET /api/v1/employees/{id}
    res = await async_client.get(f"/api/v1/employees/{mgr_id}", headers=headers)
    assert res.status_code == 200
    assert res.json()["employee_code"] == mgr_code

    # 7. PUT /api/v1/employees/{id}
    res = await async_client.put(
        f"/api/v1/employees/{sub_id}",
        json={"preferred_name": "Johnny"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["preferred_name"] == "Johnny"

    # 8. DELETE /api/v1/employees/{sub_id}
    res = await async_client.delete(f"/api/v1/employees/{sub_id}", headers=headers)
    assert res.status_code == 200
    assert res.json()["is_deleted"] is True

    # 9. PATCH /api/v1/employees/{sub_id}/restore
    res = await async_client.patch(f"/api/v1/employees/{sub_id}/restore", headers=headers)
    assert res.status_code == 200
    assert res.json()["is_deleted"] is False


@pytest.mark.asyncio
async def test_employee_rbac_unauthorized(async_client: AsyncClient):
    """
    Tests that unauthenticated requests to employee endpoints return HTTP 401.
    """
    res = await async_client.get("/api/v1/employees")
    assert res.status_code == 401

    res = await async_client.get("/api/v1/employees/hierarchy")
    assert res.status_code == 401

    res = await async_client.post("/api/v1/employees", json={"employee_code": "UNAUTH"})
    assert res.status_code == 401
