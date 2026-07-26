from fastapi import APIRouter, status
from app.core.config import settings
from app.schemas.health import HealthResponse
from app.utils.helpers import get_current_utc_time

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="System Health Check",
    description="Check health status of ApnaERP API and system components.",
    tags=["System Diagnostics"]
)
async def check_health() -> HealthResponse:
    """
    Health check endpoint returning system metadata, current UTC time, and status.
    """
    return HealthResponse(
        status="healthy",
        app_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENV,
        timestamp=get_current_utc_time(),
        components={
            "api": "operational",
            "database": "configured",
            "redis": "configured",
            "celery": "configured",
        }
    )
