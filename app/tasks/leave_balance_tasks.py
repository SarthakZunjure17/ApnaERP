import logging
from typing import Any, Dict, Optional
from app.core.celery import celery_app
from app.tasks.base import LoggingTask

logger = logging.getLogger("app.tasks.leave_balance")


@celery_app.task(
    base=LoggingTask,
    bind=True,
    name="app.tasks.leave_balance_tasks.send_leave_balance_adjustment_notification_task",
    max_retries=3,
    default_retry_delay=60,
)
def send_leave_balance_adjustment_notification_task(
    self,
    event_type: str,
    balance_id: str,
    employee_id: str,
    leave_type_id: str,
    leave_year: int,
    adjustment_type: str,
    adjustment_days: float,
    reason: str,
    new_remaining_days: float,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Asynchronous Celery task processing notification alerts for manual leave balance adjustments.
    """
    logger.info(
        f"[send_leave_balance_adjustment_notification_task] Event '{event_type}' for Employee '{employee_id}' (LeaveType: '{leave_type_id}', Year: {leave_year}, AdjType: '{adjustment_type}', Days: {adjustment_days}, Reason: '{reason}', NewRemaining: {new_remaining_days})."
    )
    return {
        "status": "success",
        "event_type": event_type,
        "balance_id": balance_id,
        "employee_id": employee_id,
        "leave_type_id": leave_type_id,
        "leave_year": leave_year,
        "adjustment_type": adjustment_type,
        "adjustment_days": adjustment_days,
        "reason": reason,
        "new_remaining_days": new_remaining_days,
        "details": details or {},
    }
