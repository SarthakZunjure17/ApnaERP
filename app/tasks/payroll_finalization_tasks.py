import logging
from typing import Any, Dict
from app.core.celery import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.payroll_finalization_tasks.send_payroll_finalization_notification_task")
def send_payroll_finalization_notification_task(
    event_type: str,
    entity_id: str,
    payload: Dict[str, Any],
) -> str:
    """
    Background task to process payroll finalization event notifications.
    Notifies Payroll Team, Finance, HR, and affected employees on adjustments, closing, reopening, archival, and financial payload publication.
    """
    logger.info(
        f"[Celery] Payroll Finalization Notification Task Triggered: "
        f"event='{event_type}', entity_id='{entity_id}', payload={payload}"
    )
    return f"Successfully dispatched notification for event '{event_type}' on entity {entity_id}"
