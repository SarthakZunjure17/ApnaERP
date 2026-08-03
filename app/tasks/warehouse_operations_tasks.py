import logging
from typing import Any, Dict

from app.core.celery import celery_app

logger = logging.getLogger("app.tasks.warehouse_operations")


@celery_app.task(name="app.tasks.warehouse_operations_tasks.send_warehouse_notification_task")
def send_warehouse_notification_task(
    event_type: str,
    payload: Dict[str, Any],
) -> str:
    """
    Background Celery task broadcasting notification telemetry for warehouse execution operations
    (Goods Receipts, Goods Issues, Stock Transfers).
    """
    logger.info(
        f"[Celery Warehouse] Telemetry Event: '{event_type}', Payload: {payload}"
    )
    return f"Successfully processed warehouse operation event '{event_type}'"
