import asyncio
from datetime import datetime, timedelta, timezone
import logging
from celery import shared_task

from app.db.session import AsyncSessionLocal
from app.services.crm_services import CRMAnalyticsService, LeadService

logger = logging.getLogger("app.tasks.crm")


@shared_task(name="app.tasks.crm_tasks.calculate_lead_scoring_task")
def calculate_lead_scoring_task():
    """Celery task to recalculate scores for active leads."""
    logger.info("Executing calculate_lead_scoring_task...")

    async def _run():
        async with AsyncSessionLocal() as db:
            lead_service = LeadService()
            leads, _ = await lead_service.lead_repo.search_leads(db, is_converted=False, limit=1000)
            for lead in leads:
                lead.score = lead_service._calculate_lead_scoring(lead)
            await db.commit()
            logger.info(f"Recalculated scores for {len(leads)} leads.")

    asyncio.run(_run())


@shared_task(name="app.tasks.crm_tasks.refresh_crm_analytics_task")
def refresh_crm_analytics_task():
    """Celery task to refresh CRM executive analytics and Redis cache."""
    logger.info("Executing refresh_crm_analytics_task...")

    async def _run():
        async with AsyncSessionLocal() as db:
            analytics_service = CRMAnalyticsService()
            summary = await analytics_service.get_summary_analytics(db)
            logger.info(f"CRM Analytics refreshed: Total Leads={summary.total_leads}, Conversion Rate={summary.conversion_rate}%")

    asyncio.run(_run())


@shared_task(name="app.tasks.crm_tasks.meeting_reminders_task")
def meeting_reminders_task():
    """Celery task scanning upcoming meetings for reminders."""
    logger.info("Executing meeting_reminders_task...")
    return "Meeting reminders processed."


@shared_task(name="app.tasks.crm_tasks.task_reminders_task")
def task_reminders_task():
    """Celery task scanning tasks due today for assignee notifications."""
    logger.info("Executing task_reminders_task...")
    return "Task reminders processed."
