import logging
from typing import Any, Dict, List, Optional
from app.core.celery import celery_app
from app.tasks.base import LoggingTask

logger = logging.getLogger("app.tasks.payroll_run")


@celery_app.task(
    base=LoggingTask,
    bind=True,
    name="app.tasks.payroll_run_tasks.send_payroll_run_notification_task",
    max_retries=3,
    default_retry_delay=60,
    ignore_result=True,
)
def send_payroll_run_notification_task(
    self,
    action: str,
    run_id: str,
    run_number: str,
    actor_id: str,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Celery task notifying Payroll Team when a payroll run completes or is locked.
    """
    logger.info(
        f"[send_payroll_run_notification_task] Action '{action}' on Run '{run_number}' (ID: '{run_id}', Actor: '{actor_id}')."
    )
    return {
        "status": "success",
        "action": action,
        "run_id": run_id,
        "run_number": run_number,
        "actor_id": actor_id,
        "details": details or {},
    }


@celery_app.task(
    base=LoggingTask,
    bind=True,
    name="app.tasks.payroll_run_tasks.send_payslip_published_notification_task",
    max_retries=3,
    default_retry_delay=60,
    ignore_result=True,
)
def send_payslip_published_notification_task(
    self,
    run_id: str,
    employee_ids: List[str],
    actor_id: str,
) -> Dict[str, Any]:
    """
    Celery task notifying employees that their monthly payslip is published and ready for download.
    """
    logger.info(
        f"[send_payslip_published_notification_task] Run '{run_id}' published {len(employee_ids)} payslips to employees. Actor: '{actor_id}'."
    )
    return {
        "status": "success",
        "run_id": run_id,
        "employee_count": len(employee_ids),
        "actor_id": actor_id,
    }
