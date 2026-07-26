import logging
from typing import Any, Dict, Optional
from app.core.celery import celery_app
from app.tasks.base import LoggingTask

logger = logging.getLogger("app.tasks.position_tasks")


@celery_app.task(
    bind=True,
    base=LoggingTask,
    name="app.tasks.position_tasks.send_position_notification_task",
    queue="default",
)
def send_position_notification_task(
    self,
    event_type: str,
    position_id: str,
    position_code: str,
    position_title: str,
    user_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Asynchronous Celery task processing Position notifications
    (POSITION_CREATE, POSITION_UPDATE, POSITION_DELETE, HEADCOUNT_LIMIT_REACHED).
    """
    logger.info(
        f"[Celery Position Notification] Event: '{event_type}' | Position: '{position_code}' ({position_title}) [ID: {position_id}]"
    )
    return {
        "status": "success",
        "event_type": event_type,
        "position_id": position_id,
        "position_code": position_code,
        "position_title": position_title,
    }
