import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user_success(async_client: AsyncClient):
    """
    Test successful user registration.
    """
    unique_id = str(uuid.uuid4())[:8]
    payload = {
        "full_name": "Test User",
        "email": f"testuser_{unique_id}@example.com",
        "username": f"testuser_{unique_id}",
        "password": "SecurePassword123!",
    }
    response = await async_client.post("/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == payload["email"]
    assert data["username"] == payload["username"]
    assert data["full_name"] == payload["full_name"]
    assert data["is_active"] is True
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(async_client: AsyncClient):
    """
    Test registration fails when email is already registered.
    """
    unique_id = str(uuid.uuid4())[:8]
    payload1 = {
        "full_name": "User One",
        "email": f"duplicate_{unique_id}@example.com",
        "username": f"userone_{unique_id}",
        "password": "Password123!",
    }
    await async_client.post("/auth/register", json=payload1)

    payload2 = {
        "full_name": "User Two",
        "email": f"duplicate_{unique_id}@example.com",
        "username": f"usertwo_{unique_id}",
        "password": "Password123!",
    }
    response = await async_client.post("/auth/register", json=payload2)
    assert response.status_code == 400
    assert "email address already exists" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_duplicate_username(async_client: AsyncClient):
    """
    Test registration fails when username is already taken.
    """
    unique_id = str(uuid.uuid4())[:8]
    payload1 = {
        "full_name": "Unique Email One",
        "email": f"unique1_{unique_id}@example.com",
        "username": f"sameusername_{unique_id}",
        "password": "Password123!",
    }
    await async_client.post("/auth/register", json=payload1)

    payload2 = {
        "full_name": "Unique Email Two",
        "email": f"unique2_{unique_id}@example.com",
        "username": f"sameusername_{unique_id}",
        "password": "Password123!",
    }
    response = await async_client.post("/auth/register", json=payload2)
    assert response.status_code == 400
    assert "username already exists" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient):
    """
    Test successful login returning JWT access and refresh tokens.
    """
    unique_id = str(uuid.uuid4())[:8]
    reg_payload = {
        "full_name": "Login User",
        "email": f"loginuser_{unique_id}@example.com",
        "username": f"loginuser_{unique_id}",
        "password": "CorrectPassword123!",
    }
    await async_client.post("/auth/register", json=reg_payload)

    login_payload = {
        "username_or_email": f"loginuser_{unique_id}@example.com",
        "password": "CorrectPassword123!",
    }
    response = await async_client.post("/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_password(async_client: AsyncClient):
    """
    Test login fails with incorrect password.
    """
    unique_id = str(uuid.uuid4())[:8]
    reg_payload = {
        "full_name": "Wrong Pass User",
        "email": f"wrongpass_{unique_id}@example.com",
        "username": f"wrongpassuser_{unique_id}",
        "password": "RightPassword123!",
    }
    await async_client.post("/auth/register", json=reg_payload)

    login_payload = {
        "username_or_email": f"wrongpassuser_{unique_id}",
        "password": "WrongPassword123!",
    }
    response = await async_client.post("/auth/login", json=login_payload)
    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_refresh_token_success(async_client: AsyncClient):
    """
    Test refreshing access token using valid refresh token.
    """
    unique_id = str(uuid.uuid4())[:8]
    reg_payload = {
        "full_name": "Refresh User",
        "email": f"refreshuser_{unique_id}@example.com",
        "username": f"refreshuser_{unique_id}",
        "password": "Password123!",
    }
    await async_client.post("/auth/register", json=reg_payload)

    login_resp = await async_client.post("/auth/login", json={
        "username_or_email": f"refreshuser_{unique_id}",
        "password": "Password123!",
    })
    tokens = login_resp.json()
    refresh_token = tokens["refresh_token"]

    refresh_resp = await async_client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_resp.status_code == 200
    new_tokens = refresh_resp.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens


@pytest.mark.asyncio
async def test_get_current_user_me(async_client: AsyncClient):
    """
    Test protected GET /auth/me endpoint returning current user details when authorized.
    """
    unique_id = str(uuid.uuid4())[:8]
    reg_payload = {
        "full_name": "Me Endpoint User",
        "email": f"meuser_{unique_id}@example.com",
        "username": f"meuser_{unique_id}",
        "password": "Password123!",
    }
    await async_client.post("/auth/register", json=reg_payload)

    login_resp = await async_client.post("/auth/login", json={
        "username_or_email": f"meuser_{unique_id}",
        "password": "Password123!",
    })
    access_token = login_resp.json()["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}
    me_resp = await async_client.get("/auth/me", headers=headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["username"] == f"meuser_{unique_id}"
    assert me_data["email"] == f"meuser_{unique_id}@example.com"


@pytest.mark.asyncio
async def test_protected_endpoint_unauthorized(async_client: AsyncClient):
    """
    Test accessing protected endpoint without token returns HTTP 401.
    """
    me_resp = await async_client.get("/auth/me")
    assert me_resp.status_code == 401
