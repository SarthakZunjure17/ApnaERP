from datetime import datetime, timezone
import logging
from typing import Any, Coroutine, TypeVar
from celery import shared_task

from app.core.celery import celery_app
from app.db.session import AsyncSessionLocal
from app.repositories.inventory_advanced_repos import batch_repository, stock_reservation_repository
from app.services.inventory_report_services import inventory_analytics_service

logger = logging.getLogger("app.tasks.inventory_advanced")

T = TypeVar("T")


def _run_async_task(coro: Coroutine[Any, Any, T]) -> T:
    """Helper to safely run coroutines inside Celery workers or active event loops."""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import nest_asyncio
        nest_asyncio.apply()
        return loop.run_until_complete(coro)
    else:
        return asyncio.run(coro)


@celery_app.task(name="app.tasks.inventory_advanced.scan_batch_expiries_task")
def scan_batch_expiries_task() -> dict:
    """Scans for expired batches, updates batch status to Expired, and sends alerts."""
    async def _scan():
        async with AsyncSessionLocal() as session:
            now = datetime.now(timezone.utc)
            expired_batches = await batch_repository.get_expiring_batches(session, before_date=now)
            count = 0
            for b in expired_batches:
                b.status = "Expired"
                count += 1
            await session.commit()
            logger.info(f"[ExpiryScanTask] Scanned and marked {count} batches as Expired.")
            return {"expired_batches_count": count}

    return _run_async_task(_scan())


@celery_app.task(name="app.tasks.inventory_advanced.cleanup_expired_reservations_task")
def cleanup_expired_reservations_task() -> dict:
    """Auto-expires outdated stock reservations."""
    async def _cleanup():
        async with AsyncSessionLocal() as session:
            now = datetime.now(timezone.utc)
            expired_res = await stock_reservation_repository.get_expired_reservations(session, now_time=now)
            count = 0
            for r in expired_res:
                r.status = "Expired"
                count += 1
            await session.commit()
            logger.info(f"[ReservationCleanupTask] Auto-expired {count} outdated stock reservations.")
            return {"expired_reservations_count": count}

    return _run_async_task(_cleanup())


@celery_app.task(name="app.tasks.inventory_advanced.refresh_inventory_analytics_task")
def refresh_inventory_analytics_task() -> dict:
    """Refreshes inventory analytics snapshot and clears dashboard cache."""
    async def _refresh():
        async with AsyncSessionLocal() as session:
            snapshot = await inventory_analytics_service.generate_analytics_snapshot(session)
            logger.info(f"[AnalyticsTask] Generated snapshot ID '{snapshot.id}' at {snapshot.snapshot_date}.")
            return {"snapshot_id": str(snapshot.id)}

    return _run_async_task(_refresh())
