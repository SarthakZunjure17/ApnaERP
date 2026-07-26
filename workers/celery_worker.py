from app.core.celery import celery_app
from app.tasks import *  # Ensure all tasks are registered

__all__ = ["celery_app"]
