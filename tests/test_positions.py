import datetime
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.core.celery import celery_app
from app.db.session import AsyncSessionLocal
from app.models.department import Department
from app.models.position import Position
from app.repositories.department import department_repository
from app.repositories.employee import employee_repository
from app.repositories.position import position_repository
from app.repositories.user import user_repository
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.schemas.position import EmploymentCategory, PositionCreate, PositionUpdate
from app.services.employee import EmployeeService
from app.services.position import PositionService


@pytest_asyncio.fixture
async def admin_token(async_client: AsyncClient) -> str:
    """Fixture creating Super Admin and returning Bearer token."""
    unique_id = uuid.uuid4().hex[:6]
    email = f"posadmin_{unique_id}@example.com"
    username = f"posadmin_{unique_id}"

    reg_payload = {
        "full_name": "Position Admin",
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
    """Fixture creating an active department."""
    async with AsyncSessionLocal() as session:
        dept = await department_repository.create(session, obj_in={
            "code": f"DEPT-POS-{uuid.uuid4().hex[:6]}",
            "name": f"Dept for Positions {uuid.uuid4().hex[:6]}",
            "is_active": True,
        })
        return dept


@pytest.mark.asyncio
async def test_position_repository_crud(test_department: Department):
    """Tests PositionRepository direct database operations."""
    async with AsyncSessionLocal() as session:
        repo = position_repository
        code = f"POS-ENG-{uuid.uuid4().hex[:6]}"

        pos = await repo.create(session, obj_in={
            "code": code,
            "title": "Lead Architect",
            "department_id": test_department.id,
            "employment_category": EmploymentCategory.PERMANENT.value,
            "maximum_headcount": 2,
            "is_active": True,
        })
        assert pos.id is not None
        assert pos.code == code
        assert pos.current_headcount == 0

        fetched_code = await repo.get_by_code(session, code)
        assert fetched_code is not None
        assert fetched_code.id == pos.id

        fetched_title = await repo.get_by_department_and_title(session, test_department.id, "Lead Architect")
        assert fetched_title is not None
        assert fetched_title.id == pos.id

        by_dept = await repo.get_by_department(session, test_department.id)
        assert len(by_dept) >= 1

        assert await repo.exists_by_code(session, code) is True

        await repo.soft_delete(session, id=pos.id)
        assert await repo.get_by_code(session, code) is None

        await repo.restore(session, id=pos.id)
        assert await repo.get_by_code(session, code) is not None


@pytest.mark.asyncio
async def test_position_service_validations(test_department: Department):
    """
    Tests PositionService business validations:
    - Unique code constraint
    - Unique title within department
    - Inactive department guard
    - Circular position hierarchy prevention
    """
    async with AsyncSessionLocal() as session:
        service = PositionService(session)
        code1 = f"POS-VAL-{uuid.uuid4().hex[:6]}"

        # 1. Create root position
        pos1 = await service.create_position(PositionCreate(
            code=code1,
            title="Director of Engineering",
            department_id=test_department.id,
            maximum_headcount=1,
            is_managerial=True,
        ))
        assert pos1.title == "Director of Engineering"

        # 2. Duplicate Code Error
        with pytest.raises(Exception) as exc_info:
            await service.create_position(PositionCreate(
                code=code1,
                title="Unique Title",
                department_id=test_department.id,
            ))
        assert "already exists" in str(exc_info.value)

        # 3. Duplicate Title in Department Error
        with pytest.raises(Exception) as exc_info:
            await service.create_position(PositionCreate(
                code=f"POS-VAL-{uuid.uuid4().hex[:6]}",
                title="Director of Engineering",
                department_id=test_department.id,
            ))
        assert "already exists in department" in str(exc_info.value)

        # 4. Inactive Department Error
        inactive_dept = await department_repository.create(session, obj_in={
            "code": f"DEPT-INACT-{uuid.uuid4().hex[:6]}",
            "name": f"Inactive Dept {uuid.uuid4().hex[:6]}",
            "is_active": False,
        })
        with pytest.raises(Exception) as exc_info:
            await service.create_position(PositionCreate(
                code=f"POS-INACT-{uuid.uuid4().hex[:6]}",
                title="Manager",
                department_id=inactive_dept.id,
            ))
        assert "inactive department" in str(exc_info.value)

        # 5. Circular Hierarchy Loop Prevention
        pos2 = await service.create_position(PositionCreate(
            code=f"POS-VAL-{uuid.uuid4().hex[:6]}",
            title="Engineering Manager",
            department_id=test_department.id,
            parent_position_id=pos1.id,
        ))

        pos3 = await service.create_position(PositionCreate(
            code=f"POS-VAL-{uuid.uuid4().hex[:6]}",
            title="Tech Lead",
            department_id=test_department.id,
            parent_position_id=pos2.id,
        ))

        # Attempt to set pos1's parent to pos3 (creates loop pos1 -> pos2 -> pos3 -> pos1)
        with pytest.raises(Exception) as exc_info:
            await service.update_position(pos1.id, PositionUpdate(parent_position_id=pos3.id))
        assert "Circular position reporting hierarchy" in str(exc_info.value) or "its own parent" in str(exc_info.value)


@pytest.mark.asyncio
async def test_employee_position_assignment_and_headcount_management(test_department: Department):
    """
    Tests automatic position headcount calculation:
    - Position maximum_headcount = 2
    - Assigning Employee 1 -> current_headcount = 1
    - Assigning Employee 2 -> current_headcount = 2
    - Assigning Employee 3 -> raises HEADCOUNT_LIMIT_EXCEEDED (HTTP 400)
    - Unassigning Employee 2 -> current_headcount decrements to 1
    - Soft-deleting Employee 1 -> current_headcount decrements to 0
    """
    async with AsyncSessionLocal() as session:
        pos_service = PositionService(session)
        emp_service = EmployeeService(session)

        pos = await pos_service.create_position(PositionCreate(
            code=f"POS-HC-{uuid.uuid4().hex[:6]}",
            title=f"Headcount Restricted Role {uuid.uuid4().hex[:6]}",
            department_id=test_department.id,
            maximum_headcount=2,
        ))
        assert pos.current_headcount == 0

        # Assign Employee 1
        emp1 = await emp_service.create_employee(EmployeeCreate(
            employee_code=f"EMP-HC-1-{uuid.uuid4().hex[:6]}",
            first_name="HC1",
            last_name="User",
            work_email=f"hc1_{uuid.uuid4().hex[:6]}@example.com",
            department_id=test_department.id,
            position_id=pos.id,
            joining_date=datetime.date(2026, 1, 1),
        ))
        updated_pos = await pos_service.get_position_by_id(pos.id)
        assert updated_pos.current_headcount == 1

        # Assign Employee 2
        emp2 = await emp_service.create_employee(EmployeeCreate(
            employee_code=f"EMP-HC-2-{uuid.uuid4().hex[:6]}",
            first_name="HC2",
            last_name="User",
            work_email=f"hc2_{uuid.uuid4().hex[:6]}@example.com",
            department_id=test_department.id,
            position_id=pos.id,
            joining_date=datetime.date(2026, 1, 1),
        ))
        updated_pos = await pos_service.get_position_by_id(pos.id)
        assert updated_pos.current_headcount == 2

        # Assign Employee 3 (Over capacity -> Error)
        with pytest.raises(Exception) as exc_info:
            await emp_service.create_employee(EmployeeCreate(
                employee_code=f"EMP-HC-3-{uuid.uuid4().hex[:6]}",
                first_name="HC3",
                last_name="User",
                work_email=f"hc3_{uuid.uuid4().hex[:6]}@example.com",
                department_id=test_department.id,
                position_id=pos.id,
                joining_date=datetime.date(2026, 1, 1),
            ))
        assert "maximum headcount capacity" in str(exc_info.value) or "HEADCOUNT_LIMIT_EXCEEDED" in str(exc_info.value)

        # Unassign Employee 2
        await emp_service.update_employee(emp2.id, EmployeeUpdate(position_id=None))
        updated_pos = await pos_service.get_position_by_id(pos.id)
        assert updated_pos.current_headcount == 1

        # Soft delete Employee 1
        await emp_service.delete_employee(emp1.id)
        updated_pos = await pos_service.get_position_by_id(pos.id)
        assert updated_pos.current_headcount == 0


@pytest.mark.asyncio
async def test_position_api_endpoints(
    async_client: AsyncClient, admin_token: str, test_department: Department
):
    """
    Tests complete Position RESTful API endpoints:
    - POST /api/v1/positions
    - GET /api/v1/positions
    - GET /api/v1/positions/tree
    - GET /api/v1/departments/{department_id}/positions
    - GET /api/v1/positions/{id}
    - PUT /api/v1/positions/{id}
    - DELETE /api/v1/positions/{id}
    - PATCH /api/v1/positions/{id}/restore
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    celery_app.conf.task_always_eager = True
    code = f"POS-API-{uuid.uuid4().hex[:6]}"

    # 1. POST /api/v1/positions
    res = await async_client.post(
        "/api/v1/positions",
        json={
            "code": code,
            "title": "API Lead Engineer",
            "description": "Leads API squad",
            "department_id": str(test_department.id),
            "employment_category": "Permanent",
            "grade": "G6",
            "level": "L5",
            "maximum_headcount": 3,
            "is_managerial": True,
        },
        headers=headers,
    )
    assert res.status_code == 201
    pos_data = res.json()
    pos_id = pos_data["id"]
    assert pos_data["code"] == code

    # 2. GET /api/v1/positions
    res = await async_client.get(f"/api/v1/positions?search={code}", headers=headers)
    assert res.status_code == 200
    assert res.json()["total"] >= 1

    # 3. GET /api/v1/positions/tree
    res = await async_client.get("/api/v1/positions/tree", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # 4. GET /api/v1/departments/{department_id}/positions
    res = await async_client.get(f"/api/v1/departments/{test_department.id}/positions", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) >= 1

    # 5. GET /api/v1/positions/{id}
    res = await async_client.get(f"/api/v1/positions/{pos_id}", headers=headers)
    assert res.status_code == 200
    assert res.json()["title"] == "API Lead Engineer"

    # 6. PUT /api/v1/positions/{id}
    res = await async_client.put(
        f"/api/v1/positions/{pos_id}",
        json={"title": "Principal API Lead Engineer", "maximum_headcount": 5},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["title"] == "Principal API Lead Engineer"
    assert res.json()["maximum_headcount"] == 5

    # 7. DELETE /api/v1/positions/{id}
    res = await async_client.delete(f"/api/v1/positions/{pos_id}", headers=headers)
    assert res.status_code == 200
    assert res.json()["is_deleted"] is True

    # 8. PATCH /api/v1/positions/{id}/restore
    res = await async_client.patch(f"/api/v1/positions/{pos_id}/restore", headers=headers)
    assert res.status_code == 200
    assert res.json()["is_deleted"] is False


@pytest.mark.asyncio
async def test_position_rbac_unauthorized(async_client: AsyncClient):
    """Tests 401 Unauthorized for unauthenticated requests."""
    res = await async_client.get("/api/v1/positions")
    assert res.status_code == 401

    res = await async_client.post("/api/v1/positions", json={"code": "POS-UNAUTH", "title": "Test"})
    assert res.status_code == 401
