from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from app.db.base import Base
from app.db.session import sync_engine
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """
    Session-wide fixture ensuring database tables exist before test execution.
    """
    Base.metadata.create_all(bind=sync_engine)
    yield


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Yields an AsyncClient bound to the FastAPI application for async testing.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
