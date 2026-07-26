import logging
from typing import Any, Dict
from app.core.celery import celery_app
from app.tasks.base import RetryTask

logger = logging.getLogger("app.tasks.document")


@celery_app.task(base=RetryTask, name="app.tasks.document_tasks.send_document_notification_task")
def send_document_notification_task(
    event: str, document_id: str, employee_id: str, document_type: str, status: str
) -> Dict[str, Any]:
    """
    Asynchronous Celery task processing background notifications for employee document events.
    """
    logger.info(
        f"[DOCUMENT TASK] Event: '{event}' | Document ID: {document_id} | Employee ID: {employee_id} | "
        f"Type: '{document_type}' | Status: '{status}'"
    )
    return {
        "status": "processed",
        "event": event,
        "document_id": document_id,
        "employee_id": employee_id,
        "document_type": document_type,
        "verification_status": status,
    }
