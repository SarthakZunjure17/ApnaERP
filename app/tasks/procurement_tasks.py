import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Dict

from sqlalchemy import select

from app.core.celery import celery_app
from app.db.session import AsyncSessionLocal
from app.models.supplier import Supplier
from app.models.supplier_quotation import SupplierQuotation
from app.repositories.procurement_repos import supplier_quotation_repository, supplier_repository
from app.services.notification_service import notification_service
from app.services.procurement_report_services import procurement_analytics_service
from app.services.supplier_services import supplier_performance_service

logger = logging.getLogger("app.tasks.procurement_tasks")


@celery_app.task(name="app.tasks.procurement_tasks.calculate_supplier_performance_task")
def calculate_supplier_performance_task() -> Dict[str, Any]:
    """
    Periodic Celery background task recalculating performance metrics for all active suppliers.
    """
    logger.info("[CeleryTask] Running calculate_supplier_performance_task...")

    async def _async_run():
        async with AsyncSessionLocal() as session:
            stmt = select(Supplier).where(Supplier.status == "Active").where(Supplier.is_deleted == False)
            res = await session.execute(stmt)
            suppliers = res.scalars().all()

            count = 0
            for s in suppliers:
                await supplier_performance_service.recalculate_supplier_performance(session, s.id)
                count += 1

            return {"processed_suppliers": count}

    loop = asyncio.get_event_loop()
    if loop.is_running():
        return loop.run_until_complete(_async_run())
    else:
        return asyncio.run(_async_run())


@celery_app.task(name="app.tasks.procurement_tasks.refresh_procurement_analytics_task")
def refresh_procurement_analytics_task() -> Dict[str, Any]:
    """
    Daily Celery background task calculating and persisting Procurement Analytics snapshots.
    """
    logger.info("[CeleryTask] Running refresh_procurement_analytics_task...")

    async def _async_run():
        async with AsyncSessionLocal() as session:
            snapshot = await procurement_analytics_service.generate_analytics_snapshot(session)
            return {"snapshot_id": str(snapshot.id), "snapshot_date": snapshot.snapshot_date.isoformat()}

    loop = asyncio.get_event_loop()
    if loop.is_running():
        return loop.run_until_complete(_async_run())
    else:
        return asyncio.run(_async_run())


@celery_app.task(name="app.tasks.procurement_tasks.check_expiring_quotations_task")
def check_expiring_quotations_task() -> Dict[str, Any]:
    """
    Daily Celery task flagging expired supplier quotations.
    """
    logger.info("[CeleryTask] Running check_expiring_quotations_task...")

    async def _async_run():
        async with AsyncSessionLocal() as session:
            now = datetime.now(timezone.utc)
            stmt = (
                select(SupplierQuotation)
                .where(SupplierQuotation.status.in_(["Submitted", "Under Review"]))
                .where(SupplierQuotation.validity_date <= now)
            )
            res = await session.execute(stmt)
            expired_q = res.scalars().all()

            count = 0
            for q in expired_q:
                q.status = "Expired"
                count += 1

            if count > 0:
                await session.commit()

            return {"expired_quotations_count": count}

    loop = asyncio.get_event_loop()
    if loop.is_running():
        return loop.run_until_complete(_async_run())
    else:
        return asyncio.run(_async_run())
