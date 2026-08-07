import asyncio
import logging
from celery import shared_task
from app.db.session import AsyncSessionLocal

logger = logging.getLogger("app.tasks.reporting")


@shared_task(name="app.tasks.reporting_tasks.process_scheduled_reports_task")
def process_scheduled_reports_task() -> str:
    """
    Celery task to run due scheduled reports and send notifications.
    """
    from app.services.reporting_services import ScheduledReportService

    async def _run():
        async with AsyncSessionLocal() as session:
            service = ScheduledReportService(session)
            count = await service.process_scheduled_reports()
            return count

    loop = asyncio.get_event_loop()
    if loop.is_running():
        count = asyncio.run_coroutine_threadsafe(_run(), loop).result()
    else:
        count = loop.run_until_complete(_run())

    return f"Processed {count} scheduled reports successfully."


@shared_task(name="app.tasks.reporting_tasks.refresh_analytics_snapshots_task")
def refresh_analytics_snapshots_task() -> str:
    """
    Celery task to pre-calculate periodic analytics snapshots.
    """
    from app.services.reporting_services import AnalyticsService

    async def _run():
        async with AsyncSessionLocal() as session:
            service = AnalyticsService(session)
            modules = ["HR", "Payroll", "Inventory", "Procurement", "Sales", "CRM", "Finance"]
            for m in modules:
                await service.compute_analytics_snapshot(m, f"{m}Health")
            return len(modules)

    loop = asyncio.get_event_loop()
    if loop.is_running():
        count = asyncio.run_coroutine_threadsafe(_run(), loop).result()
    else:
        count = loop.run_until_complete(_run())

    return f"Refreshed analytics snapshots for {count} modules."


@shared_task(name="app.tasks.reporting_tasks.refresh_kpis_task")
def refresh_kpis_task() -> str:
    """
    Celery task to refresh active KPIs.
    """
    from app.services.reporting_services import KPIService

    async def _run():
        async with AsyncSessionLocal() as session:
            service = KPIService(session)
            kpi_codes = ["KPI-EMP-ACTIVE", "KPI-FIN-REV", "KPI-FIN-EXP", "KPI-INV-VAL", "KPI-SALES-VOL"]
            for code in kpi_codes:
                try:
                    await service.calculate_kpi(code)
                except Exception as exc:
                    logger.warning(f"KPI calculation skipped for {code}: {exc}")
            return len(kpi_codes)

    loop = asyncio.get_event_loop()
    if loop.is_running():
        count = asyncio.run_coroutine_threadsafe(_run(), loop).result()
    else:
        count = loop.run_until_complete(_run())

    return f"Refreshed {count} system KPIs."
