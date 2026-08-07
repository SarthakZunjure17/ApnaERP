from fastapi import APIRouter
from app.schemas.integrations import HealthCheckResponse
from app.services.integration_services import DeploymentService

router = APIRouter()


@router.get("/health", response_model=HealthCheckResponse)
@router.get("/health/liveness", response_model=HealthCheckResponse)
@router.get("/health/readiness", response_model=HealthCheckResponse)
async def check_health():
    service = DeploymentService()
    return await service.get_health_status()
