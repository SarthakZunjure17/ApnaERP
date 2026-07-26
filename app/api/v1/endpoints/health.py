from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db
from app.core.config import settings
from app.db.session import check_db_connectivity
from app.schemas.health import DatabaseHealthResponse, HealthResponse
from app.utils.helpers import get_current_utc_time

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="System Health Check",
    description="Check overall health status of ApnaERP API and system components.",
    tags=["System Diagnostics"]
)
async def check_health(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """
    Health check endpoint returning system metadata, current UTC time, and database connectivity.
    """
    db_status = await check_db_connectivity(db)
    
    return HealthResponse(
        status="healthy" if db_status.get("status") == "connected" else "degraded",
        app_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENV,
        timestamp=get_current_utc_time(),
        components={
            "api": "operational",
            "database": db_status,
            "redis": "configured",
            "celery": "configured",
        }
    )


@router.get(
    "/health/db",
    response_model=DatabaseHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Database Connectivity Check",
    description="Executes a live query ('SELECT 1') to verify PostgreSQL database connection.",
    tags=["System Diagnostics"]
)
async def check_database_health(db: AsyncSession = Depends(get_db)) -> DatabaseHealthResponse:
    """
    Dedicated database health check endpoint.
    """
    db_status = await check_db_connectivity(db)
    return DatabaseHealthResponse(
        status=db_status.get("status", "disconnected"),
        latency_ms=db_status.get("latency_ms"),
        database=db_status.get("database"),
        error=db_status.get("error"),
    )
