import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.core.redis import redis_manager
from app.db.base import Base
from app.db.seed_rbac import seed_rbac_data
from app.db.session import AsyncSessionLocal, engine

logger = logging.getLogger("app.events")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event context manager handling startup and shutdown events for FastAPI.
    """
    # Startup tasks
    logger.info(f"Starting {settings.PROJECT_NAME} (v{settings.VERSION}) in [{settings.ENV}] mode...")
    
    # 1. Initialize Redis Infrastructure
    try:
        await redis_manager.init_redis()
    except Exception as exc:
        logger.warning(f"Redis initialization warning: {exc}")

    # 2. Ensure Database Schema & RBAC Seed Data
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with AsyncSessionLocal() as session:
            await seed_rbac_data(session)
        logger.info("Database tables verified and RBAC seed data completed successfully.")
    except Exception as exc:
        logger.warning(f"Database startup initialization note: {exc}")

    yield
    
    # Shutdown tasks
    logger.info(f"Shutting down {settings.PROJECT_NAME} gracefully...")
    await redis_manager.close_redis()
    await engine.dispose()
    logger.info("Database engine & Redis connections closed cleanly.")
