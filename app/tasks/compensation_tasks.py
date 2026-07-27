import logging
from typing import Any, Dict, Optional
from app.core.celery import celery_app
from app.tasks.base import LoggingTask

logger = logging.getLogger("app.tasks.compensation")


@celery_app.task(
    base=LoggingTask,
    bind=True,
    name="app.tasks.compensation_tasks.send_compensation_notification_task",
    max_retries=3,
    default_retry_delay=60,
)
def send_compensation_notification_task(
    self,
    action: str,
    compensation_id: str,
    employee_id: str,
    salary_structure_id: str,
    annual_ctc: float,
    status: str,
    performed_by_id: str,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Asynchronous Celery task notifying HR and Employees of compensation policy modifications.
    """
    logger.info(
        f"[send_compensation_notification_task] Action '{action}' on Compensation '{compensation_id}' (Employee: '{employee_id}', Structure: '{salary_structure_id}', CTC: {annual_ctc}, Status: '{status}', PerformedBy: '{performed_by_id}')."
    )
    return {
        "status": "success",
        "action": action,
        "compensation_id": compensation_id,
        "employee_id": employee_id,
        "salary_structure_id": salary_structure_id,
        "annual_ctc": annual_ctc,
        "compensation_status": status,
        "performed_by_id": performed_by_id,
        "details": details or {},
    }
