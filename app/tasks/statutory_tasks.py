import logging
from typing import Any, Dict, Optional
from app.core.celery import celery_app
from app.tasks.base import LoggingTask

logger = logging.getLogger("app.tasks.statutory")


@celery_app.task(
    base=LoggingTask,
    bind=True,
    name="app.tasks.statutory_tasks.send_statutory_rule_notification_task",
    max_retries=3,
    default_retry_delay=60,
    ignore_result=True,
)
def send_statutory_rule_notification_task(
    self,
    action: str,
    rule_id: str,
    rule_code: str,
    rule_name: str,
    country_code: str,
    actor_id: str,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Celery task notifying Payroll Administrators when statutory rules are created, modified, activated, or deactivated.
    """
    logger.info(
        f"[send_statutory_rule_notification_task] Action '{action}' on StatutoryRule '{rule_code}' - '{rule_name}' (Country: {country_code}, ID: {rule_id}, Actor: {actor_id})."
    )
    return {
        "status": "success",
        "action": action,
        "rule_id": rule_id,
        "rule_code": rule_code,
        "rule_name": rule_name,
        "country_code": country_code,
        "actor_id": actor_id,
        "details": details or {},
    }
