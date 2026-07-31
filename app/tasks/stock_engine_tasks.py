import asyncio
from decimal import Decimal
import logging
from typing import Optional
import uuid

from app.core.celery import celery_app
from app.db.session import AsyncSessionLocal

logger = logging.getLogger("app.tasks.stock_engine")


def _run_async_task(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    else:
        return loop.create_task(coro)


@celery_app.task(name="app.tasks.stock_engine_tasks.refresh_stock_balance_task")
def refresh_stock_balance_task(product_id_str: str, warehouse_id_str: str, location_id_str: Optional[str] = None):
    """
    Celery background task that recalculates StockBalance projection from StockLedger history asynchronously.
    """
    async def _run():
        from app.services.stock_engine_services import stock_balance_service
        async with AsyncSessionLocal() as session:
            p_id = uuid.UUID(product_id_str)
            w_id = uuid.UUID(warehouse_id_str)
            l_id = uuid.UUID(location_id_str) if location_id_str else None
            await stock_balance_service.recalculate_balance_projection(session, p_id, w_id, l_id)
            logger.info(f"[Task] Successfully refreshed stock balance projection for Product {p_id}, Warehouse {w_id}.")

    return _run_async_task(_run())


@celery_app.task(name="app.tasks.stock_engine_tasks.detect_balance_inconsistencies_task")
def detect_balance_inconsistencies_task():
    """
    Celery background task scanning StockBalance records and verifying against StockLedger totals.
    Repairs detected discrepancies automatically.
    """
    async def _run():
        from sqlalchemy import select
        from app.models.stock_balance import StockBalance
        from app.services.stock_engine_services import stock_balance_service

        repaired_count = 0
        async with AsyncSessionLocal() as session:
            balances = (await session.execute(select(StockBalance))).scalars().all()
            for b in balances:
                recalculated = await stock_balance_service.recalculate_balance_projection(
                    session, b.product_id, b.warehouse_id, b.storage_location_id
                )
                if recalculated.available_quantity != b.available_quantity:
                    repaired_count += 1
            logger.info(f"[Task] Inconsistency audit complete. Scanned {len(balances)} balances, repaired {repaired_count}.")
        return repaired_count

    return _run_async_task(_run())


@celery_app.task(name="app.tasks.stock_engine_tasks.send_stock_notification_task")
def send_stock_notification_task(event_name: str, details: str) -> str:
    """
    Celery background task broadcasting notification telemetry for stock movements and approvals.
    """
    logger.info(f"[Task Notification] Event: '{event_name}', Details: '{details}'")
    return f"Successfully processed stock notification for event '{event_name}'"
