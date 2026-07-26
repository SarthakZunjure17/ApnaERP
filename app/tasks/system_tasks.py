import logging
from datetime import datetime, timezone
from typing import Any, Dict

from app.core.celery import celery_app
from app.tasks.base import LoggingTask, RetryTask

logger = logging.getLogger("app.tasks.system")


@celery_app.task(base=LoggingTask, name="app.tasks.system_tasks.system_ping_task")
def system_ping_task(payload: str = "ping") -> Dict[str, Any]:
    """
    Heartbeat ping task to verify active Celery worker execution.
    """
    logger.info(f"[SYSTEM TASK] Ping payload: '{payload}'")
    return {
        "status": "pong",
        "payload": payload,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@celery_app.task(base=RetryTask, name="app.tasks.system_tasks.system_health_check_task")
def system_health_check_task() -> Dict[str, Any]:
    """
    Asynchronous system diagnostic task testing worker execution pipeline.
    """
    logger.info("[SYSTEM TASK] Executing Celery worker health diagnostic check.")
    return {
        "health": "healthy",
        "worker_engine": "celery",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
