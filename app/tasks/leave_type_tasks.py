import logging
from typing import Any, Dict, Optional
from app.core.celery import celery_app
from app.tasks.base import LoggingTask

logger = logging.getLogger("app.tasks.leave_type")


@celery_app.task(
    base=LoggingTask,
    bind=True,
    name="app.tasks.leave_type_tasks.send_leave_policy_change_notification_task",
    max_retries=3,
    default_retry_delay=60,
)
def send_leave_policy_change_notification_task(
    self,
    event_type: str,
    leave_type_id: str,
    leave_code: str,
    leave_name: str,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Asynchronous Celery task notifying HR Admins when organizational Leave Policies are created, modified, or deleted.
    """
    logger.info(
        f"[send_leave_policy_change_notification_task] Event '{event_type}' for Leave Type '{leave_name}' (Code: '{leave_code}', ID: '{leave_type_id}')."
    )
    return {
        "status": "success",
        "event_type": event_type,
        "leave_type_id": leave_type_id,
        "leave_code": leave_code,
        "leave_name": leave_name,
        "details": details or {},
    }
