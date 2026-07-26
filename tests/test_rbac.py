import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient
from app.db.session import AsyncSessionLocal
from app.repositories.user import user_repository


@pytest_asyncio.fixture
async def superuser_headers(async_client: AsyncClient):
    """
    Fixture registering a superuser and returning Bearer authorization headers.
    """
    unique_id = uuid.uuid4().hex[:6]
    email = f"superadmin_{unique_id}@example.com"
    username = f"superadmin_{unique_id}"
    
    reg_payload = {
        "full_name": "Super Admin User",
        "email": email,
        "username": username,
        "password": "SuperPassword123!",
    }
    reg_resp = await async_client.post("/auth/register", json=reg_payload)
    user_id = uuid.UUID(reg_resp.json()["id"])
    
    # Mark user as superuser in DB
    async with AsyncSessionLocal() as session:
        user = await user_repository.get_by_id(session, user_id)
        if user:
            user.is_superuser = True
            await session.commit()
    
    login_resp = await async_client.post("/auth/login", json={
        "username_or_email": email,
        "password": "SuperPassword123!",
    })
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def regular_user_headers(async_client: AsyncClient):
    """
    Fixture registering a regular user without permissions and returning Bearer headers.
    """
    unique_id = uuid.uuid4().hex[:6]
    email = f"regular_{unique_id}@example.com"
    username = f"regularuser_{unique_id}"

    reg_payload = {
        "full_name": "Regular User",
        "email": email,
        "username": username,
        "password": "RegularPassword123!",
    }
    await async_client.post("/auth/register", json=reg_payload)
    login_resp = await async_client.post("/auth/login", json={
        "username_or_email": email,
        "password": "RegularPassword123!",
    })
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_get_roles_authenticated(async_client: AsyncClient, regular_user_headers: dict):
    """
    Test listing roles returns 200 OK for authenticated user.
    """
    response = await async_client.get("/roles", headers=regular_user_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1  # Default roles seeded


@pytest.mark.asyncio
async def test_create_permission_and_role(async_client: AsyncClient, superuser_headers: dict):
    """
    Test superuser can create a custom permission and custom role.
    """
    unique_id = uuid.uuid4().hex[:6]
    # 1. Create Permission
    perm_payload = {
        "name": f"Custom Test Action {unique_id}",
        "code": f"test.custom_action_{unique_id}",
        "description": "Permission for testing custom action",
        "module_name": "test_module",
    }
    perm_resp = await async_client.post("/permissions", json=perm_payload, headers=superuser_headers)
    assert perm_resp.status_code == 201
    perm_data = perm_resp.json()
    perm_id = perm_data["id"]

    # 2. Create Role with permission attached
    role_payload = {
        "name": f"Custom Test Role {unique_id}",
        "description": "Custom role for testing",
        "permission_ids": [perm_id],
    }
    role_resp = await async_client.post("/roles", json=role_payload, headers=superuser_headers)
    assert role_resp.status_code == 201
    role_data = role_resp.json()
    assert role_data["name"] == f"Custom Test Role {unique_id}"
    assert len(role_data["permissions"]) == 1
    assert role_data["permissions"][0]["code"] == f"test.custom_action_{unique_id}"


@pytest.mark.asyncio
async def test_assign_role_to_user(async_client: AsyncClient, superuser_headers: dict):
    """
    Test assigning a role to a registered user.
    """
    unique_id = uuid.uuid4().hex[:6]
    # Create regular user
    reg_payload = {
        "full_name": "Target User",
        "email": f"targetuser_{unique_id}@example.com",
        "username": f"targetuser_{unique_id}",
        "password": "Password123!",
    }
    reg_resp = await async_client.post("/auth/register", json=reg_payload)
    user_id = reg_resp.json()["id"]

    # Get roles list
    roles_resp = await async_client.get("/roles", headers=superuser_headers)
    roles = roles_resp.json()
    target_role = next(r for r in roles if r["name"] == "HR Manager")

    # Assign HR Manager role to user
    assign_resp = await async_client.post(
        f"/users/{user_id}/roles",
        json={"role_id": target_role["id"]},
        headers=superuser_headers,
    )
    assert assign_resp.status_code == 200
    assert "assigned" in assign_resp.json()["message"].lower()


@pytest.mark.asyncio
async def test_unauthorized_access(async_client: AsyncClient):
    """
    Test accessing protected RBAC endpoint without Bearer token returns 401 Unauthorized.
    """
    response = await async_client.get("/roles")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_forbidden_access(async_client: AsyncClient, regular_user_headers: dict):
    """
    Test regular user without permissions receives 403 Forbidden when creating roles.
    """
    unique_id = uuid.uuid4().hex[:6]
    role_payload = {
        "name": f"Unauthorized Role {unique_id}",
        "description": "Attempting role creation",
    }
    response = await async_client.post("/roles", json=role_payload, headers=regular_user_headers)
    assert response.status_code == 403
    assert "forbidden" in response.json()["detail"].lower() or "denied" in response.json()["detail"].lower()
