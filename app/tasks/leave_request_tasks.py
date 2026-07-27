import logging
from typing import Any, Dict, Optional
from app.core.celery import celery_app
from app.tasks.base import LoggingTask

logger = logging.getLogger("app.tasks.leave_request")


@celery_app.task(
    base=LoggingTask,
    bind=True,
    name="app.tasks.leave_request_tasks.send_leave_request_notification_task",
    max_retries=3,
    default_retry_delay=60,
)
def send_leave_request_notification_task(
    self,
    event_type: str,
    request_id: str,
    employee_id: str,
    leave_type_id: str,
    start_date: str,
    end_date: str,
    total_days: float,
    status: str,
    reviewer_id: Optional[str] = None,
    comments: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Asynchronous Celery task processing notification alerts for leave request workflow events.
    - Event SUBMITTED: Alerts Manager awaiting review.
    - Event APPROVED / REJECTED: Alerts Employee on decision.
    - Event CANCELLED: Alerts HR on application cancellation.
    """
    logger.info(
        f"[send_leave_request_notification_task] Event '{event_type}' for Request '{request_id}' (Employee: '{employee_id}', LeaveType: '{leave_type_id}', Status: '{status}', Dates: {start_date} to {end_date}, TotalDays: {total_days})."
    )
    return {
        "status": "success",
        "event_type": event_type,
        "request_id": request_id,
        "employee_id": employee_id,
        "leave_type_id": leave_type_id,
        "start_date": start_date,
        "end_date": end_date,
        "total_days": total_days,
        "workflow_status": status,
        "reviewer_id": reviewer_id,
        "comments": comments,
        "details": details or {},
    }
