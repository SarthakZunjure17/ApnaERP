import logging
from typing import Any, Dict, Optional
from app.core.celery import celery_app
from app.tasks.base import LoggingTask

logger = logging.getLogger("app.tasks.attendance")


@celery_app.task(
    base=LoggingTask,
    bind=True,
    name="app.tasks.attendance_tasks.send_attendance_notification_task",
    max_retries=3,
    default_retry_delay=60,
)
def send_attendance_notification_task(
    self,
    event_type: str,
    attendance_id: str,
    employee_id: str,
    attendance_date: str,
    attendance_status: str,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Asynchronous Celery task processing Attendance notifications.
    Triggered on Late Arrival, Missing Checkout, Manual Corrections, or Lock events.
    """
    logger.info(
        f"[send_attendance_notification_task] Event '{event_type}' for Employee '{employee_id}' on '{attendance_date}' (Status: '{attendance_status}', ID: '{attendance_id}')."
    )
    return {
        "status": "success",
        "event_type": event_type,
        "attendance_id": attendance_id,
        "employee_id": employee_id,
        "attendance_date": attendance_date,
        "attendance_status": attendance_status,
        "details": details or {},
    }
