import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.core.celery import celery_app
from app.core.redis import redis_manager
from app.db.session import AsyncSessionLocal
from app.models.department import Department
from app.models.user import User
from app.repositories.department import department_repository
from app.repositories.user import user_repository
from app.schemas.department import DepartmentCreate, DepartmentUpdate
from app.services.department import CACHE_TREE_KEY, DepartmentService


@pytest_asyncio.fixture
async def admin_token(async_client: AsyncClient) -> str:
    """
    Helper fixture registering a superuser and returning Bearer JWT token.
    """
    unique_id = uuid.uuid4().hex[:6]
    email = f"deptadmin_{unique_id}@example.com"
    username = f"deptadmin_{unique_id}"

    reg_payload = {
        "full_name": "Dept Admin User",
        "email": email,
        "username": username,
        "password": "AdminPassword123!",
    }
    reg_resp = await async_client.post("/api/v1/auth/register", json=reg_payload)
    user_id = uuid.UUID(reg_resp.json()["id"])

    # Mark user as superuser in DB
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
async def test_department_repository_crud():
    """
    Tests DepartmentRepository direct database operations.
    """
    async with AsyncSessionLocal() as session:
        repo = department_repository
        code = f"TEST-REPO-{uuid.uuid4().hex[:6]}"
        name = f"Test Repo Dept {uuid.uuid4().hex[:6]}"

        dept = await repo.create(session, obj_in={
            "code": code,
            "name": name,
            "description": "Direct Repo Test",
            "is_active": True,
        })
        assert dept.id is not None
        assert dept.code == code

        fetched = await repo.get_by_code(session, code)
        assert fetched is not None
        assert fetched.id == dept.id

        assert await repo.exists_by_code(session, code) is True
        assert await repo.exists_by_name(session, name) is True

        # Soft delete & restore
        await repo.soft_delete(session, id=dept.id)
        assert await repo.get_by_code(session, code) is None
        assert (await repo.get_by_code(session, code, include_deleted=True)) is not None

        await repo.restore(session, id=dept.id)
        assert await repo.get_by_code(session, code) is not None


@pytest.mark.asyncio
async def test_department_service_business_rules():
    """
    Tests DepartmentService validation rules:
    - Unique code & name
    - Circular parent prevention
    - Active children deletion protection
    """
    async with AsyncSessionLocal() as session:
        service = DepartmentService(session)
        code1 = f"CORP-{uuid.uuid4().hex[:6]}"
        code2 = f"HR-{uuid.uuid4().hex[:6]}"

        # 1. Create Parent Dept
        parent = await service.create_department(DepartmentCreate(
            code=code1, name=f"Corp Parent {uuid.uuid4().hex[:6]}", description="Parent Dept"
        ))

        # 2. Duplicate Code Error
        with pytest.raises(Exception) as exc_info:
            await service.create_department(DepartmentCreate(
                code=code1, name=f"Other Name {uuid.uuid4().hex[:6]}"
            ))
        assert "already exists" in str(exc_info.value)

        # 3. Create Child Dept
        child = await service.create_department(DepartmentCreate(
            code=code2, name=f"HR Child {uuid.uuid4().hex[:6]}", parent_id=parent.id
        ))

        # 4. Circular Parent Validation Error (Setting parent's parent to child)
        with pytest.raises(Exception) as exc_info:
            await service.update_department(parent.id, DepartmentUpdate(parent_id=child.id))
        assert "Circular parent department reference" in str(exc_info.value)

        # 5. Active Children Deletion Guard
        with pytest.raises(Exception) as exc_info:
            await service.delete_department(parent.id)
        assert "has active child departments" in str(exc_info.value)

        # 6. Delete Child first, then Parent can be deleted
        await service.delete_department(child.id)
        deleted_parent = await service.delete_department(parent.id)
        assert deleted_parent.is_deleted is True


@pytest.mark.asyncio
async def test_department_api_endpoints(async_client: AsyncClient, admin_token: str):
    """
    Tests full API endpoint workflow for Department Management:
    - POST /api/v1/departments
    - GET /api/v1/departments/tree
    - GET /api/v1/departments
    - GET /api/v1/departments/{id}
    - PUT /api/v1/departments/{id}
    - DELETE /api/v1/departments/{id}
    - PATCH /api/v1/departments/{id}/restore
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    celery_app.conf.task_always_eager = True

    # 1. Create Root Department
    root_code = f"ENG-{uuid.uuid4().hex[:6]}"
    res = await async_client.post(
        "/api/v1/departments",
        json={
            "code": root_code,
            "name": f"Engineering {uuid.uuid4().hex[:6]}",
            "description": "Engineering Division",
            "is_active": True,
        },
        headers=headers,
    )
    assert res.status_code == 201
    root_data = res.json()
    root_id = root_data["id"]

    # 2. Create Child Department
    child_code = f"BE-{uuid.uuid4().hex[:6]}"
    res = await async_client.post(
        "/api/v1/departments",
        json={
            "code": child_code,
            "name": f"Backend Team {uuid.uuid4().hex[:6]}",
            "description": "Backend Team",
            "parent_id": root_id,
            "is_active": True,
        },
        headers=headers,
    )
    assert res.status_code == 201
    child_data = res.json()
    child_id = child_data["id"]

    # 3. GET /api/v1/departments/tree
    res = await async_client.get("/api/v1/departments/tree", headers=headers)
    assert res.status_code == 200
    tree_data = res.json()
    assert isinstance(tree_data, list)
    matching_roots = [d for d in tree_data if d["id"] == root_id]
    assert len(matching_roots) == 1
    assert len(matching_roots[0]["children"]) >= 1

    # 4. GET /api/v1/departments (List)
    res = await async_client.get("/api/v1/departments", headers=headers)
    assert res.status_code == 200
    list_data = res.json()
    assert list_data["total"] >= 2

    # 5. GET /api/v1/departments/{id}
    res = await async_client.get(f"/api/v1/departments/{root_id}", headers=headers)
    assert res.status_code == 200
    assert res.json()["code"] == root_code

    # 6. PUT /api/v1/departments/{id}
    updated_name = f"Updated Eng {uuid.uuid4().hex[:6]}"
    res = await async_client.put(
        f"/api/v1/departments/{root_id}",
        json={"name": updated_name},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["name"] == updated_name

    # 7. DELETE /api/v1/departments/{child_id}
    res = await async_client.delete(f"/api/v1/departments/{child_id}", headers=headers)
    assert res.status_code == 200
    assert res.json()["is_deleted"] is True

    # 8. PATCH /api/v1/departments/{child_id}/restore
    res = await async_client.patch(f"/api/v1/departments/{child_id}/restore", headers=headers)
    assert res.status_code == 200
    assert res.json()["is_deleted"] is False


@pytest.mark.asyncio
async def test_department_rbac_unauthorized(async_client: AsyncClient):
    """
    Tests that unauthenticated users cannot access department endpoints (401 Unauthorized).
    """
    res = await async_client.get("/api/v1/departments")
    assert res.status_code == 401

    res = await async_client.post("/api/v1/departments", json={"code": "FAIL", "name": "Fail"})
    assert res.status_code == 401
