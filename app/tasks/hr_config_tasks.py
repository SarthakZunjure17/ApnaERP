import logging
from typing import Any, Dict, Optional
from app.core.celery import celery_app
from app.tasks.base import LoggingTask

logger = logging.getLogger("app.tasks.hr_config")


@celery_app.task(
    base=LoggingTask,
    bind=True,
    name="app.tasks.hr_config_tasks.send_hr_config_notification_task",
    max_retries=3,
    default_retry_delay=60,
)
def send_hr_config_notification_task(
    self,
    event_type: str,
    config_id: str,
    organization_code: str,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Asynchronous Celery task processing HR Configuration notifications.
    Fired when an HR Configuration is created, updated, or activated.
    """
    logger.info(
        f"[send_hr_config_notification_task] Processing event '{event_type}' for HR Configuration ID '{config_id}' (Org: '{organization_code}')."
    )
    return {
        "status": "success",
        "event_type": event_type,
        "config_id": config_id,
        "organization_code": organization_code,
        "triggered_by_user_id": user_id,
    }
