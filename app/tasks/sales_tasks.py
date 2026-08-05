import asyncio
import logging
from celery import shared_task

from app.db.session import AsyncSessionLocal
from app.services.quotation_services import quotation_service
from app.services.sales_analytics_services import sales_analytics_service

logger = logging.getLogger("app.tasks.sales")


@shared_task(name="app.tasks.sales_tasks.refresh_sales_analytics_task")
def refresh_sales_analytics_task() -> str:
    """Celery background task to refresh sales analytics and capture snapshot."""
    async def _run():
        async with AsyncSessionLocal() as session:
            snapshot = await sales_analytics_service.refresh_sales_analytics_snapshot(session)
            return str(snapshot.id)

    loop = asyncio.get_event_loop()
    if loop.is_running():
        snapshot_id = asyncio.run_coroutine_threadsafe(_run(), loop).result()
    else:
        snapshot_id = loop.run_until_complete(_run())

    logger.info(f"Sales analytics snapshot created with ID: {snapshot_id}")
    return snapshot_id


@shared_task(name="app.tasks.sales_tasks.generate_daily_revenue_summary_task")
def generate_daily_revenue_summary_task() -> dict:
    """Celery background task to aggregate daily sales revenue metrics."""
    async def _run():
        async with AsyncSessionLocal() as session:
            analytics = await sales_analytics_service.get_analytics_summary(session)
            return {
                "total_revenue": float(analytics.total_revenue),
                "total_orders": analytics.total_orders,
                "avg_order_value": float(analytics.avg_order_value),
            }

    loop = asyncio.get_event_loop()
    if loop.is_running():
        summary = asyncio.run_coroutine_threadsafe(_run(), loop).result()
    else:
        summary = loop.run_until_complete(_run())

    logger.info(f"Daily revenue summary generated: {summary}")
    return summary


@shared_task(name="app.tasks.sales_tasks.check_expired_quotations_task")
def check_expired_quotations_task() -> int:
    """Celery background task to scan and expire past-due sales quotations."""
    async def _run():
        async with AsyncSessionLocal() as session:
            return await quotation_service.expire_quotations(session)

    loop = asyncio.get_event_loop()
    if loop.is_running():
        expired_count = asyncio.run_coroutine_threadsafe(_run(), loop).result()
    else:
        expired_count = loop.run_until_complete(_run())

    logger.info(f"Expired {expired_count} sales quotations")
    return expired_count


@shared_task(name="app.tasks.sales_tasks.send_delivery_reminders_task")
def send_delivery_reminders_task() -> int:
    """Celery background task to send delivery status reminders to warehouse & sales teams."""
    logger.info("Delivery reminders task executed")
    return 0


@shared_task(name="app.tasks.sales_tasks.send_order_reminders_task")
def send_order_reminders_task() -> int:
    """Celery background task to send unapproved or pending order reminders."""
    logger.info("Order reminders task executed")
    return 0
