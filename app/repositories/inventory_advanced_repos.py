from datetime import datetime, timezone
from decimal import Decimal
import uuid
from typing import Any, List, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.batch import Batch
from app.models.cycle_count import CycleCount, CycleCountItem
from app.models.inventory_analytics_snapshot import InventoryAnalyticsSnapshot
from app.models.lot import Lot
from app.models.serial_number import SerialNumber
from app.models.stock_reservation import StockReservation
from app.repositories.base import BaseRepository


from app.schemas.inventory_advanced import (
    BatchCreate,
    BatchUpdate,
    CycleCountCreate,
    LotCreate,
    LotUpdate,
    SerialNumberCreate,
    SerialNumberUpdate,
    StockReservationCreate,
)


class BatchRepository(BaseRepository[Batch, BatchCreate, BatchUpdate]):
    def __init__(self):
        super().__init__(Batch)


    async def get_by_number(self, db: AsyncSession, batch_number: str) -> Optional[Batch]:
        stmt = select(Batch).where(Batch.batch_number == batch_number)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi_paginated(
        self,
        db: AsyncSession,
        product_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Batch], int]:
        stmt = select(Batch)
        if product_id:
            stmt = stmt.where(Batch.product_id == product_id)
        if status:
            stmt = stmt.where(Batch.status == status)
        if search:
            stmt = stmt.where(Batch.batch_number.ilike(f"%{search}%"))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_res = await db.execute(count_stmt)
        total = total_res.scalar() or 0

        stmt = stmt.order_by(Batch.expiry_date.asc().nulls_last(), Batch.created_at.desc()).offset(skip).limit(limit)
        res = await db.execute(stmt)
        return list(res.scalars().all()), total

    async def get_expiring_batches(
        self, db: AsyncSession, before_date: datetime
    ) -> List[Batch]:
        stmt = (
            select(Batch)
            .where(Batch.status == "Active")
            .where(Batch.expiry_date.isnot(None))
            .where(Batch.expiry_date <= before_date)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())


class SerialNumberRepository(BaseRepository[SerialNumber, SerialNumberCreate, SerialNumberUpdate]):
    def __init__(self):
        super().__init__(SerialNumber)

    async def get_by_number(self, db: AsyncSession, serial_number: str) -> Optional[SerialNumber]:
        stmt = select(SerialNumber).where(SerialNumber.serial_number == serial_number)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi_paginated(
        self,
        db: AsyncSession,
        product_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[SerialNumber], int]:
        stmt = select(SerialNumber)
        if product_id:
            stmt = stmt.where(SerialNumber.product_id == product_id)
        if warehouse_id:
            stmt = stmt.where(SerialNumber.warehouse_id == warehouse_id)
        if status:
            stmt = stmt.where(SerialNumber.status == status)
        if search:
            stmt = stmt.where(SerialNumber.serial_number.ilike(f"%{search}%"))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_res = await db.execute(count_stmt)
        total = total_res.scalar() or 0

        stmt = stmt.order_by(SerialNumber.created_at.desc()).offset(skip).limit(limit)
        res = await db.execute(stmt)
        return list(res.scalars().all()), total


class LotRepository(BaseRepository[Lot, LotCreate, LotUpdate]):
    def __init__(self):
        super().__init__(Lot)

    async def get_by_number(self, db: AsyncSession, lot_number: str) -> Optional[Lot]:
        stmt = select(Lot).where(Lot.lot_number == lot_number)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi_paginated(
        self,
        db: AsyncSession,
        product_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Lot], int]:
        stmt = select(Lot)
        if product_id:
            stmt = stmt.where(Lot.product_id == product_id)
        if search:
            stmt = stmt.where(
                or_(
                    Lot.lot_number.ilike(f"%{search}%"),
                    Lot.production_lot.ilike(f"%{search}%"),
                    Lot.supplier_lot.ilike(f"%{search}%"),
                )
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_res = await db.execute(count_stmt)
        total = total_res.scalar() or 0

        stmt = stmt.order_by(Lot.created_at.desc()).offset(skip).limit(limit)
        res = await db.execute(stmt)
        return list(res.scalars().all()), total


class StockReservationRepository(BaseRepository[StockReservation, StockReservationCreate, Any]):
    def __init__(self):
        super().__init__(StockReservation)

    async def get_by_number(self, db: AsyncSession, reservation_number: str) -> Optional[StockReservation]:
        stmt = select(StockReservation).where(StockReservation.reservation_number == reservation_number)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_reserved_quantity(
        self,
        db: AsyncSession,
        product_id: uuid.UUID,
        warehouse_id: Optional[uuid.UUID] = None,
    ) -> Decimal:
        stmt = (
            select(func.coalesce(func.sum(StockReservation.quantity), Decimal("0.0")))
            .where(StockReservation.product_id == product_id)
            .where(StockReservation.status == "Active")
        )
        if warehouse_id:
            stmt = stmt.where(StockReservation.warehouse_id == warehouse_id)

        res = await db.execute(stmt)
        val = res.scalar()
        return Decimal(str(val)) if val is not None else Decimal("0.0")

    async def get_expired_reservations(self, db: AsyncSession, now_time: datetime) -> List[StockReservation]:
        stmt = (
            select(StockReservation)
            .where(StockReservation.status == "Active")
            .where(StockReservation.expires_at.isnot(None))
            .where(StockReservation.expires_at <= now_time)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def get_multi_paginated(
        self,
        db: AsyncSession,
        product_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[StockReservation], int]:
        stmt = select(StockReservation)
        if product_id:
            stmt = stmt.where(StockReservation.product_id == product_id)
        if warehouse_id:
            stmt = stmt.where(StockReservation.warehouse_id == warehouse_id)
        if status:
            stmt = stmt.where(StockReservation.status == status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_res = await db.execute(count_stmt)
        total = total_res.scalar() or 0

        stmt = stmt.order_by(StockReservation.created_at.desc()).offset(skip).limit(limit)
        res = await db.execute(stmt)
        return list(res.scalars().all()), total


class CycleCountRepository(BaseRepository[CycleCount, CycleCountCreate, Any]):
    def __init__(self):
        super().__init__(CycleCount)

    async def get_by_number(self, db: AsyncSession, count_number: str) -> Optional[CycleCount]:
        stmt = (
            select(CycleCount)
            .options(selectinload(CycleCount.items))
            .where(CycleCount.count_number == count_number)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi_paginated(
        self,
        db: AsyncSession,
        warehouse_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[CycleCount], int]:
        stmt = select(CycleCount).options(selectinload(CycleCount.items))
        if warehouse_id:
            stmt = stmt.where(CycleCount.warehouse_id == warehouse_id)
        if status:
            stmt = stmt.where(CycleCount.status == status)

        count_stmt = select(func.count()).select_from(select(CycleCount.id).where(
            *([CycleCount.warehouse_id == warehouse_id] if warehouse_id else []),
            *([CycleCount.status == status] if status else []),
        ).subquery())
        total_res = await db.execute(count_stmt)
        total = total_res.scalar() or 0

        stmt = stmt.order_by(CycleCount.created_at.desc()).offset(skip).limit(limit)
        res = await db.execute(stmt)
        return list(res.scalars().all()), total


class InventoryAnalyticsRepository(BaseRepository[InventoryAnalyticsSnapshot, Any, Any]):
    def __init__(self):
        super().__init__(InventoryAnalyticsSnapshot)


    async def get_latest_snapshot(self, db: AsyncSession) -> Optional[InventoryAnalyticsSnapshot]:
        stmt = select(InventoryAnalyticsSnapshot).order_by(InventoryAnalyticsSnapshot.snapshot_date.desc()).limit(1)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()


batch_repository = BatchRepository()
serial_number_repository = SerialNumberRepository()
lot_repository = LotRepository()
stock_reservation_repository = StockReservationRepository()
cycle_count_repository = CycleCountRepository()
inventory_analytics_repository = InventoryAnalyticsRepository()
