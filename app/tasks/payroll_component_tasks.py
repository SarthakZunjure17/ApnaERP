import logging
from typing import Any, Dict, Optional
from app.core.celery import celery_app
from app.tasks.base import LoggingTask

logger = logging.getLogger("app.tasks.payroll_component")


@celery_app.task(
    base=LoggingTask,
    bind=True,
    name="app.tasks.payroll_component_tasks.send_payroll_component_notification_task",
    max_retries=3,
    default_retry_delay=60,
)
def send_payroll_component_notification_task(
    self,
    action: str,
    component_id: str,
    code: str,
    name: str,
    component_type: str,
    calculation_method: str,
    performed_by_id: str,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Asynchronous Celery task notifying Payroll Administrators of Salary Component modifications.
    """
    logger.info(
        f"[send_payroll_component_notification_task] Action '{action}' on Component '{code}' ({name}, Type: '{component_type}', Method: '{calculation_method}', ID: '{component_id}', PerformedBy: '{performed_by_id}')."
    )
    return {
        "status": "success",
        "action": action,
        "component_id": component_id,
        "code": code,
        "name": name,
        "component_type": component_type,
        "calculation_method": calculation_method,
        "performed_by_id": performed_by_id,
        "details": details or {},
    }
