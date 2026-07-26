import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient):
    """
    Test root GET / endpoint response code and schema structure.
    """
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "app_name" in data
    assert "version" in data
    assert data["docs_url"] == "/docs"
