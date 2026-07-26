import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user_success(async_client: AsyncClient):
    """
    Test successful user registration.
    """
    payload = {
        "full_name": "Test User",
        "email": "testuser@example.com",
        "username": "testuser",
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
    payload1 = {
        "full_name": "User One",
        "email": "duplicate@example.com",
        "username": "userone",
        "password": "Password123!",
    }
    await async_client.post("/auth/register", json=payload1)

    payload2 = {
        "full_name": "User Two",
        "email": "duplicate@example.com",
        "username": "usertwo",
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
    payload1 = {
        "full_name": "Unique Email One",
        "email": "unique1@example.com",
        "username": "sameusername",
        "password": "Password123!",
    }
    await async_client.post("/auth/register", json=payload1)

    payload2 = {
        "full_name": "Unique Email Two",
        "email": "unique2@example.com",
        "username": "sameusername",
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
    reg_payload = {
        "full_name": "Login User",
        "email": "loginuser@example.com",
        "username": "loginuser",
        "password": "CorrectPassword123!",
    }
    await async_client.post("/auth/register", json=reg_payload)

    login_payload = {
        "username_or_email": "loginuser@example.com",
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
    reg_payload = {
        "full_name": "Wrong Pass User",
        "email": "wrongpass@example.com",
        "username": "wrongpassuser",
        "password": "RightPassword123!",
    }
    await async_client.post("/auth/register", json=reg_payload)

    login_payload = {
        "username_or_email": "wrongpassuser",
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
    reg_payload = {
        "full_name": "Refresh User",
        "email": "refreshuser@example.com",
        "username": "refreshuser",
        "password": "Password123!",
    }
    await async_client.post("/auth/register", json=reg_payload)

    login_resp = await async_client.post("/auth/login", json={
        "username_or_email": "refreshuser",
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
    reg_payload = {
        "full_name": "Me Endpoint User",
        "email": "meuser@example.com",
        "username": "meuser",
        "password": "Password123!",
    }
    await async_client.post("/auth/register", json=reg_payload)

    login_resp = await async_client.post("/auth/login", json={
        "username_or_email": "meuser",
        "password": "Password123!",
    })
    access_token = login_resp.json()["access_token"]

    # Request /auth/me with Bearer token header
    headers = {"Authorization": f"Bearer {access_token}"}
    me_resp = await async_client.get("/auth/me", headers=headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["username"] == "meuser"
    assert me_data["email"] == "meuser@example.com"


@pytest.mark.asyncio
async def test_protected_endpoint_unauthorized(async_client: AsyncClient):
    """
    Test accessing protected endpoint without token returns HTTP 401.
    """
    me_resp = await async_client.get("/auth/me")
    assert me_resp.status_code == 401
