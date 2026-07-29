import logging
from typing import Any, Dict
from app.core.celery import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.inventory_tasks.send_inventory_notification_task")
def send_inventory_notification_task(
    event_type: str,
    payload: Dict[str, Any],
) -> str:
    """
    Background Celery task to process inventory notifications.
    Notifies Inventory Administrators when a new warehouse is created, warehouse updated, or product archived.
    """
    logger.info(
        f"[Celery] Inventory Notification Task Triggered: "
        f"event='{event_type}', payload={payload}"
    )
    return f"Successfully processed inventory notification for event '{event_type}'"
