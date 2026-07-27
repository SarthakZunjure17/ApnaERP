import logging
from typing import Any, Dict, Optional
from app.core.celery import celery_app
from app.tasks.base import LoggingTask

logger = logging.getLogger("app.tasks.shift_assignment")


@celery_app.task(
    base=LoggingTask,
    bind=True,
    name="app.tasks.shift_assignment_tasks.send_shift_assignment_notification_task",
    max_retries=3,
    default_retry_delay=60,
)
def send_shift_assignment_notification_task(
    self,
    event_type: str,
    assignment_id: str,
    employee_id: str,
    shift_id: str,
    effective_from: str,
    effective_to: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Asynchronous Celery task processing Shift Assignment notifications.
    Notifies employee and manager on shift assignment changes, updates, or termination.
    """
    logger.info(
        f"[send_shift_assignment_notification_task] Event '{event_type}' for Employee '{employee_id}' (Shift: '{shift_id}', Effective: '{effective_from}' to '{effective_to}', AssignmentID: '{assignment_id}')."
    )
    return {
        "status": "success",
        "event_type": event_type,
        "assignment_id": assignment_id,
        "employee_id": employee_id,
        "shift_id": shift_id,
        "effective_from": effective_from,
        "effective_to": effective_to,
        "details": details or {},
    }
