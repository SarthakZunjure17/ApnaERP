import logging
from typing import Any, Dict, Optional
from app.core.celery import celery_app
from app.tasks.base import LoggingTask

logger = logging.getLogger("app.tasks.holiday")


@celery_app.task(
    base=LoggingTask,
    bind=True,
    name="app.tasks.holiday_tasks.send_holiday_notification_task",
    max_retries=3,
    default_retry_delay=60,
)
def send_holiday_notification_task(
    self,
    event_type: str,
    holiday_id: str,
    holiday_code: str,
    holiday_name: str,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Asynchronous Celery task processing Holiday notifications.
    Fired when a Holiday calendar entry is created, updated, or deleted.
    """
    logger.info(
        f"[send_holiday_notification_task] Processing event '{event_type}' for Holiday '{holiday_name}' (Code: '{holiday_code}', ID: '{holiday_id}')."
    )
    return {
        "status": "success",
        "event_type": event_type,
        "holiday_id": holiday_id,
        "holiday_code": holiday_code,
        "holiday_name": holiday_name,
        "triggered_by_user_id": user_id,
    }
