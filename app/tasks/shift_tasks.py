import logging
from typing import Any, Dict, Optional
from app.core.celery import celery_app
from app.tasks.base import LoggingTask

logger = logging.getLogger("app.tasks.shift")


@celery_app.task(
    base=LoggingTask,
    bind=True,
    name="app.tasks.shift_tasks.send_shift_notification_task",
    max_retries=3,
    default_retry_delay=60,
)
def send_shift_notification_task(
    self,
    event_type: str,
    shift_id: str,
    shift_code: str,
    shift_name: str,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Asynchronous Celery task processing Shift notifications.
    Fired when a Shift schedule is created, updated, or deleted.
    """
    logger.info(
        f"[send_shift_notification_task] Processing event '{event_type}' for Shift '{shift_name}' (Code: '{shift_code}', ID: '{shift_id}')."
    )
    return {
        "status": "success",
        "event_type": event_type,
        "shift_id": shift_id,
        "shift_code": shift_code,
        "shift_name": shift_name,
        "triggered_by_user_id": user_id,
    }
