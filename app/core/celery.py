import logging
from celery import Celery
from kombu import Exchange, Queue

from app.core.config import settings

logger = logging.getLogger("app.core.celery")

# Initialize Celery application
celery_app = Celery(
    "apnaerp",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Kombu Exchange & Queue Definitions
default_exchange = Exchange("default", type="direct")
media_exchange = Exchange("media", type="direct")
periodic_exchange = Exchange("periodic", type="direct")

task_queues = (
    Queue("default", default_exchange, routing_key="default", queue_arguments={"x-max-priority": 10}),
    Queue("high_priority", default_exchange, routing_key="high_priority", queue_arguments={"x-max-priority": 10}),
    Queue("low_priority", default_exchange, routing_key="low_priority", queue_arguments={"x-max-priority": 10}),
    Queue("periodic", periodic_exchange, routing_key="periodic"),
)

# Celery Configuration Mapping
celery_app.conf.update(
    timezone=settings.CELERY_TIMEZONE,
    enable_utc=True,
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    result_serializer=settings.CELERY_RESULT_SERIALIZER,
    accept_content=settings.CELERY_ACCEPT_CONTENT,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=240,
    worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,
    worker_prefetch_multiplier=1,
    task_queues=task_queues,
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",
    task_routes={
        "app.tasks.system_tasks.*": {"queue": "high_priority"},
        "app.tasks.notification_tasks.*": {"queue": "high_priority"},
        "app.tasks.report_tasks.*": {"queue": "low_priority"},
    },
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=True,
)

# Auto-discover tasks in 'app.tasks' package
celery_app.autodiscover_tasks(["app.tasks"])


def get_celery_app() -> Celery:
    """
    Returns the initialized Celery application instance.
    """
    return celery_app
