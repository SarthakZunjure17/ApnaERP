import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.db.session import engine

logger = logging.getLogger("app.events")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event context manager handling startup and shutdown events for FastAPI.
    """
    # Startup tasks
    logger.info(f"Starting {settings.PROJECT_NAME} (v{settings.VERSION}) in [{settings.ENV}] mode...")
    
    yield
    
    # Shutdown tasks
    logger.info(f"Shutting down {settings.PROJECT_NAME} gracefully...")
    await engine.dispose()
    logger.info("Database engine connections closed.")
