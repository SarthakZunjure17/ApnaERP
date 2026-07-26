import logging
from typing import Any, Dict
from app.core.celery import celery_app
from app.tasks.base import RetryTask

logger = logging.getLogger("app.tasks.department")


@celery_app.task(base=RetryTask, name="app.tasks.department_tasks.send_department_notification_task")
def send_department_notification_task(event: str, department_id: str, code: str, name: str) -> Dict[str, Any]:
    """
    Asynchronous Celery task processing background notifications for department events.
    """
    logger.info(f"[DEPARTMENT TASK] Event: '{event}' for Department '{name}' ({code}, ID: {department_id})")
    return {
        "status": "processed",
        "event": event,
        "department_id": department_id,
        "code": code,
        "name": name,
    }
