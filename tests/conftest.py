import asyncio
from typing import AsyncGenerator
import pytest
import pytest_asyncio
import fakeredis.aioredis
from httpx import ASGITransport, AsyncClient
from app.core.redis import redis_manager
from app.db.base import Base
from app.db.seed_rbac import seed_rbac_data
from app.db.session import AsyncSessionLocal, sync_engine
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """
    Session-wide fixture ensuring database tables exist and RBAC seed data is present.
    """
    Base.metadata.create_all(bind=sync_engine)
    
    async def run_seed():
        async with AsyncSessionLocal() as session:
            await seed_rbac_data(session)
            
    asyncio.run(run_seed())
    yield


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_redis():
    """
    Session-wide fixture setting up in-memory FakeRedis for pytest suite.
    """
    fake_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    redis_manager._client = fake_client
    yield
    await fake_client.aclose()


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Yields an AsyncClient bound to the FastAPI application for async testing.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
