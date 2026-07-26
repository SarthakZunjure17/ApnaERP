import logging
from typing import Any, Dict
from app.core.celery import celery_app
from app.tasks.base import RetryTask

logger = logging.getLogger("app.tasks.employee")


@celery_app.task(base=RetryTask, name="app.tasks.employee_tasks.send_employee_notification_task")
def send_employee_notification_task(event: str, employee_id: str, code: str, email: str) -> Dict[str, Any]:
    """
    Asynchronous Celery task processing background notifications for employee events.
    """
    logger.info(f"[EMPLOYEE TASK] Event: '{event}' for Employee Code: '{code}', Email: '{email}', ID: {employee_id}")
    return {
        "status": "processed",
        "event": event,
        "employee_id": employee_id,
        "code": code,
        "email": email,
    }
