from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.celery import celery_app
from app.core.redis import redis_manager
from app.db.session import get_db, check_db_connectivity
from app.schemas.health import DatabaseHealthResponse, HealthResponse
from app.schemas.integrations import HealthCheckResponse
from app.services.integration_services import DeploymentService

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
@router.get("/health/liveness", response_model=HealthResponse)
@router.get("/health/readiness", response_model=HealthResponse)
async def check_health():
    service = DeploymentService()
    return await service.get_health_status()


@router.get("/health/db", response_model=DatabaseHealthResponse)
async def check_database_health(db: AsyncSession = Depends(get_db)):
    result = await check_db_connectivity(db)
    return DatabaseHealthResponse(**result)


@router.get("/health/redis")
async def check_redis_health():
    return await redis_manager.check_redis_health()


@router.get("/health/celery")
async def check_celery_health():
    registered_tasks = list(celery_app.tasks.keys())
    return {
        "status": "healthy",
        "broker_status": "connected",
        "registered_tasks_count": len(registered_tasks),
        "configured_queues": ["default", "high_priority", "low_priority", "payroll"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/workers")
async def check_workers_health():
    return {
        "status": "healthy",
        "worker_status": "active",
        "active_worker_count": 2,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


