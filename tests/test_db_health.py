import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_db_health_endpoint(async_client: AsyncClient):
    """
    Test dedicated database health check GET /health/db endpoint.
    """
    response = await async_client.get("/health/db")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ["connected", "disconnected"]


@pytest.mark.asyncio
async def test_v1_db_health_endpoint(async_client: AsyncClient):
    """
    Test database health check GET /api/v1/health/db endpoint.
    """
    response = await async_client.get("/api/v1/health/db")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
