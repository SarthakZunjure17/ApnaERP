import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
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
    try:
        async with AsyncSessionLocal() as session:
            await seed_rbac_data(session)
        logger.info("RBAC seed data check completed successfully.")
    except Exception as exc:
        logger.warning(f"Skipping RBAC startup seed (database tables may not exist yet): {exc}")

    yield
    
    # Shutdown tasks
    logger.info(f"Shutting down {settings.PROJECT_NAME} gracefully...")
    await engine.dispose()
    logger.info("Database engine connections closed.")
