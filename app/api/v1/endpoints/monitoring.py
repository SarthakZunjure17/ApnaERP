from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.schemas.integrations import SystemMetricsResponse
from app.services.integration_services import MonitoringService

router = APIRouter()


@router.get("/metrics/summary", response_model=SystemMetricsResponse)
async def get_system_metrics_summary(
    current_user: User = Depends(get_current_user),
):
    service = MonitoringService()
    return service.get_metrics_summary()


@router.get("/metrics", response_class=PlainTextResponse)
async def get_prometheus_metrics():
    service = MonitoringService()
    return service.generate_prometheus_format()
