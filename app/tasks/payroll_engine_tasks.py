import logging
from typing import Any, Dict, Optional
from app.core.celery import celery_app
from app.tasks.base import LoggingTask

logger = logging.getLogger("app.tasks.payroll_engine")


@celery_app.task(
    base=LoggingTask,
    bind=True,
    name="app.tasks.payroll_engine_tasks.send_payroll_notification_task",
    max_retries=3,
    default_retry_delay=60,
    ignore_result=True,
)
def send_payroll_notification_task(
    self,
    action: str,
    period_id: str,
    period_code: str,
    total_records: int,
    total_net_salary: float,
    status: str,
    performed_by_id: str,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Asynchronous Celery task notifying Payroll Team, HR, and Finance of payroll processing operations.
    """
    logger.info(
        f"[send_payroll_notification_task] Action '{action}' on Period '{period_code}' (ID: '{period_id}', Records: {total_records}, NetSalary: {total_net_salary}, Status: '{status}', PerformedBy: '{performed_by_id}')."
    )
    return {
        "status": "success",
        "action": action,
        "period_id": period_id,
        "period_code": period_code,
        "total_records": total_records,
        "total_net_salary": total_net_salary,
        "payroll_status": status,
        "performed_by_id": performed_by_id,
        "details": details or {},
    }
