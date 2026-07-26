import logging
import time
from typing import Any, Dict, Optional, Tuple
import celery
from celery import Task
from app.exceptions.base import ApnaERPException

logger = logging.getLogger("app.tasks.base")


class BaseTask(Task):
    """
    Abstract Base Task class for all ApnaERP asynchronous background tasks.
    Enforces structured logging, correlation tracking, and failure/retry hooks.
    """
    abstract = True

    def on_success(self, retval: Any, task_id: str, args: Tuple[Any, ...], kwargs: Dict[str, Any]) -> None:
        """
        Success callback hook executed when task completes cleanly.
        """
        logger.info(f"[CELERY SUCCESS] Task '{self.name}' (ID: {task_id}) completed successfully.")
        super().on_success(retval, task_id, args, kwargs)

    def on_failure(self, exc: Exception, task_id: str, args: Tuple[Any, ...], kwargs: Dict[str, Any], einfo: Any) -> None:
        """
        Failure callback hook executed when task fails with unhandled exception.
        """
        logger.error(f"[CELERY FAILURE] Task '{self.name}' (ID: {task_id}) failed: {exc}", exc_info=einfo)
        super().on_failure(exc, task_id, args, kwargs, einfo)

    def on_retry(self, exc: Exception, task_id: str, args: Tuple[Any, ...], kwargs: Dict[str, Any], einfo: Any) -> None:
        """
        Retry callback hook executed when task is scheduled for retry.
        """
        logger.warning(f"[CELERY RETRY] Task '{self.name}' (ID: {task_id}) retrying due to: {exc}")
        super().on_retry(exc, task_id, args, kwargs, einfo)


class RetryTask(BaseTask):
    """
    Base task class configured with exponential backoff auto-retry policies.
    """
    abstract = True
    autoretry_for = (Exception,)
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True
    max_retries = 3


class PeriodicTask(BaseTask):
    """
    Base task class for scheduled periodic tasks (Celery Beat).
    """
    abstract = True
    queue = "periodic"


class LoggingTask(BaseTask):
    """
    Base task class providing verbose execution telemetry and runtime timing logs.
    """
    abstract = True

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        start_time = time.perf_counter()
        logger.info(f"[TASK START] Executing '{self.name}'...")
        try:
            result = super().__call__(*args, **kwargs)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.info(f"[TASK END] Executed '{self.name}' in {duration_ms} ms.")
            return result
        except Exception as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(f"[TASK ERROR] '{self.name}' failed after {duration_ms} ms: {e}")
            raise
