import logging
import os
import sys
import time
from typing import AsyncGenerator, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from app.core.config import settings

logger = logging.getLogger("app.db")

# Detect if running within pytest test runner
IS_TESTING = settings.ENV == "test" or "pytest" in os.environ.get("_", "") or (hasattr(sys, "argv") and any("pytest" in arg for arg in sys.argv))

db_async_url = settings.async_database_url
db_sync_url = settings.sync_database_url

if IS_TESTING or os.environ.get("USE_SQLITE", "").lower() in ("true", "1"):
    if not db_async_url.startswith("sqlite"):
        db_async_url = "sqlite+aiosqlite:///./apnaerp_test.db"
        db_sync_url = "sqlite:///./apnaerp_test.db"

is_sqlite = db_async_url.startswith("sqlite")

# Configure engine arguments based on environment
engine_kwargs: Dict[str, Any] = {
    "echo": settings.DEBUG if not IS_TESTING else False,
    "future": True,
}

if not is_sqlite:
    engine_kwargs["pool_pre_ping"] = True
    if IS_TESTING:
        engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs["pool_size"] = 10
        engine_kwargs["max_overflow"] = 20

# Create Async Engine for FastAPI async operations
engine = create_async_engine(
    db_async_url,
    **engine_kwargs
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

sync_engine_kwargs: Dict[str, Any] = {
    "echo": settings.DEBUG if not IS_TESTING else False,
}
if not is_sqlite:
    sync_engine_kwargs["pool_pre_ping"] = True

# Create Sync Engine for Alembic migrations & synchronous tasks
sync_engine = create_engine(
    db_sync_url,
    **sync_engine_kwargs
)

# Sync session factory
SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency yielding an async SQLAlchemy session.
    Automatically closes session after HTTP request completion.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def check_db_connectivity(session: AsyncSession) -> Dict[str, Any]:
    """
    Utility function to verify live database connectivity by executing a lightweight query.
    Returns status, response time, and database dialect metadata.
    """
    start_time = time.time()
    try:
        result = await session.execute(text("SELECT 1"))
        val = result.scalar()
        latency_ms = (time.time() - start_time) * 1000
        if val == 1:
            return {
                "status": "connected",
                "latency_ms": round(latency_ms, 2),
                "database": settings.POSTGRES_DB,
            }
        else:
            return {
                "status": "error",
                "message": "Unexpected query result",
                "latency_ms": round(latency_ms, 2),
            }
    except Exception as exc:
        logger.error(f"Database connectivity check failed: {exc}", exc_info=True)
        return {
            "status": "disconnected",
            "error": str(exc),
        }
