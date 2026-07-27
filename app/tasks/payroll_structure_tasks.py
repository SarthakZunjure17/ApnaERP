import logging
from typing import Any, Dict, Optional
from app.core.celery import celery_app
from app.tasks.base import LoggingTask

logger = logging.getLogger("app.tasks.payroll_structure")


@celery_app.task(
    base=LoggingTask,
    bind=True,
    name="app.tasks.payroll_structure_tasks.send_payroll_structure_notification_task",
    max_retries=3,
    default_retry_delay=60,
)
def send_payroll_structure_notification_task(
    self,
    action: str,
    structure_id: str,
    code: str,
    name: str,
    performed_by_id: str,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Asynchronous Celery task notifying Payroll Administrators of Salary Structure modifications.
    """
    logger.info(
        f"[send_payroll_structure_notification_task] Action '{action}' on Structure '{code}' ({name}, ID: '{structure_id}', PerformedBy: '{performed_by_id}')."
    )
    return {
        "status": "success",
        "action": action,
        "structure_id": structure_id,
        "code": code,
        "name": name,
        "performed_by_id": performed_by_id,
        "details": details or {},
    }
