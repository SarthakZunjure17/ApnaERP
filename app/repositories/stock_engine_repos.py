from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory_adjustment import InventoryAdjustment
from app.models.inventory_transaction_type import InventoryTransactionType
from app.models.opening_stock import OpeningStock
from app.models.stock_balance import StockBalance
from app.models.stock_ledger import StockLedger
from app.repositories.base import BaseRepository
from app.schemas.stock_engine import (
    InventoryAdjustmentCreate,
    InventoryAdjustmentUpdate,
    InventoryTransactionTypeCreate,
    OpeningStockCreate,
)


class InventoryTransactionTypeRepository(BaseRepository[InventoryTransactionType, InventoryTransactionTypeCreate, Any]):
    """
    Repository for managing InventoryTransactionType records.
    """
    def __init__(self):
        super().__init__(InventoryTransactionType)

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[InventoryTransactionType]:
        result = await db.execute(
            select(InventoryTransactionType).where(func.upper(InventoryTransactionType.code) == code.upper())
        )
        return result.scalars().first()

    async def get_all_active(self, db: AsyncSession) -> List[InventoryTransactionType]:
        result = await db.execute(
            select(InventoryTransactionType).where(InventoryTransactionType.is_active == True).order_by(InventoryTransactionType.code)
        )
        return list(result.scalars().all())


class StockLedgerRepository(BaseRepository[StockLedger, Any, Any]):
    """
    Repository for managing immutable StockLedger records.
    """
    def __init__(self):
        super().__init__(StockLedger)

    async def get_latest_running_balance(
        self,
        db: AsyncSession,
        product_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        storage_location_id: Optional[uuid.UUID] = None,
    ) -> Decimal:
        """
        Retrieves the running balance from the most recent ledger entry for a product/warehouse/location.
        """
        stmt = select(StockLedger.running_balance).where(
            StockLedger.product_id == product_id,
            StockLedger.warehouse_id == warehouse_id,
        )
        if storage_location_id:
            stmt = stmt.where(StockLedger.storage_location_id == storage_location_id)

        stmt = stmt.order_by(StockLedger.transaction_date.desc(), StockLedger.created_at.desc()).limit(1)
        result = await db.execute(stmt)
        val = result.scalar_one_or_none()
        return Decimal(str(val)) if val is not None else Decimal("0.0")

    async def create_ledger_entry(self, db: AsyncSession, obj_in: Dict[str, Any]) -> StockLedger:
        """
        Inserts an immutable ledger entry.
        """
        ledger = StockLedger(**obj_in)
        db.add(ledger)
        await db.commit()
        await db.refresh(ledger)
        return ledger

    async def get_ledger_entries_paginated(
        self,
        db: AsyncSession,
        product_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        storage_location_id: Optional[uuid.UUID] = None,
        transaction_type_id: Optional[uuid.UUID] = None,
        reference_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        search_term: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[StockLedger], int]:
        """
        Queries stock ledger entries with multi-column filtering, search, and pagination.
        """
        stmt = select(StockLedger)
        count_stmt = select(func.count(StockLedger.id))

        filters = []
        if product_id:
            filters.append(StockLedger.product_id == product_id)
        if warehouse_id:
            filters.append(StockLedger.warehouse_id == warehouse_id)
        if storage_location_id:
            filters.append(StockLedger.storage_location_id == storage_location_id)
        if transaction_type_id:
            filters.append(StockLedger.transaction_type_id == transaction_type_id)
        if reference_type:
            filters.append(func.lower(StockLedger.reference_type) == reference_type.lower())
        if start_date:
            filters.append(StockLedger.transaction_date >= start_date)
        if end_date:
            filters.append(StockLedger.transaction_date <= end_date)

        if search_term:
            search_pattern = f"%{search_term}%"
            filters.append(
                or_(
                    StockLedger.reference_type.ilike(search_pattern),
                    StockLedger.remarks.ilike(search_pattern),
                    StockLedger.direction.ilike(search_pattern),
                )
            )

        if filters:
            stmt = stmt.where(and_(*filters))
            count_stmt = count_stmt.where(and_(*filters))

        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(StockLedger.transaction_date.desc(), StockLedger.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    async def calculate_derived_balance_from_history(
        self,
        db: AsyncSession,
        product_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        storage_location_id: Optional[uuid.UUID] = None,
    ) -> Decimal:
        """
        Derives current available stock quantity by summing historical IN vs OUT ledger movements.
        """
        stmt = select(StockLedger).where(
            StockLedger.product_id == product_id,
            StockLedger.warehouse_id == warehouse_id,
        )
        if storage_location_id:
            stmt = stmt.where(StockLedger.storage_location_id == storage_location_id)

        result = await db.execute(stmt)
        entries = result.scalars().all()

        total = Decimal("0.0")
        for e in entries:
            qty = Decimal(str(e.quantity))
            if e.direction == "IN":
                total += qty
            elif e.direction == "OUT":
                total -= qty
            elif e.direction == "ADJUSTMENT":
                total += qty  # positive or negative qty for adjustment
            elif e.direction == "SYSTEM":
                total += qty
        return total


class StockBalanceRepository(BaseRepository[StockBalance, Any, Any]):
    """
    Repository for managing StockBalance projection records.
    """
    def __init__(self):
        super().__init__(StockBalance)

    async def get_by_keys(
        self,
        db: AsyncSession,
        product_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        storage_location_id: Optional[uuid.UUID] = None,
    ) -> Optional[StockBalance]:
        stmt = select(StockBalance).where(
            StockBalance.product_id == product_id,
            StockBalance.warehouse_id == warehouse_id,
        )
        if storage_location_id:
            stmt = stmt.where(StockBalance.storage_location_id == storage_location_id)
        else:
            stmt = stmt.where(StockBalance.storage_location_id.is_(None))

        result = await db.execute(stmt)
        return result.scalars().first()

    async def upsert_balance(
        self,
        db: AsyncSession,
        product_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        storage_location_id: Optional[uuid.UUID],
        available_quantity: Decimal,
        reserved_quantity: Decimal = Decimal("0.0"),
        damaged_quantity: Decimal = Decimal("0.0"),
        in_transit_quantity: Decimal = Decimal("0.0"),
    ) -> StockBalance:
        existing = await self.get_by_keys(db, product_id, warehouse_id, storage_location_id)
        now = datetime.now(timezone.utc)
        if existing:
            existing.available_quantity = available_quantity
            existing.reserved_quantity = reserved_quantity
            existing.damaged_quantity = damaged_quantity
            existing.in_transit_quantity = in_transit_quantity
            existing.last_calculated = now
            await db.commit()
            await db.refresh(existing)
            return existing
        else:
            bal = StockBalance(
                product_id=product_id,
                warehouse_id=warehouse_id,
                storage_location_id=storage_location_id,
                available_quantity=available_quantity,
                reserved_quantity=reserved_quantity,
                damaged_quantity=damaged_quantity,
                in_transit_quantity=in_transit_quantity,
                last_calculated=now,
            )
            db.add(bal)
            await db.commit()
            await db.refresh(bal)
            return bal

    async def get_balances_by_product(self, db: AsyncSession, product_id: uuid.UUID) -> List[StockBalance]:
        result = await db.execute(
            select(StockBalance).where(StockBalance.product_id == product_id)
        )
        return list(result.scalars().all())

    async def get_balances_by_warehouse(self, db: AsyncSession, warehouse_id: uuid.UUID) -> List[StockBalance]:
        result = await db.execute(
            select(StockBalance).where(StockBalance.warehouse_id == warehouse_id)
        )
        return list(result.scalars().all())

    async def get_balances_by_location(self, db: AsyncSession, location_id: uuid.UUID) -> List[StockBalance]:
        result = await db.execute(
            select(StockBalance).where(StockBalance.storage_location_id == location_id)
        )
        return list(result.scalars().all())


class OpeningStockRepository(BaseRepository[OpeningStock, OpeningStockCreate, Any]):
    """
    Repository for managing OpeningStock records.
    """
    def __init__(self):
        super().__init__(OpeningStock)

    async def exists_by_reference(self, db: AsyncSession, reference_number: str) -> bool:
        result = await db.execute(
            select(func.count(OpeningStock.id)).where(OpeningStock.reference_number == reference_number)
        )
        return (result.scalar() or 0) > 0

    async def exists_by_product_warehouse_location(
        self,
        db: AsyncSession,
        product_id: uuid.UUID,
        warehouse_id: uuid.UUID,
        location_id: Optional[uuid.UUID] = None,
    ) -> bool:
        stmt = select(func.count(OpeningStock.id)).where(
            OpeningStock.product_id == product_id,
            OpeningStock.warehouse_id == warehouse_id,
        )
        if location_id:
            stmt = stmt.where(OpeningStock.location_id == location_id)
        else:
            stmt = stmt.where(OpeningStock.location_id.is_(None))

        result = await db.execute(stmt)
        return (result.scalar() or 0) > 0


class InventoryAdjustmentRepository(BaseRepository[InventoryAdjustment, InventoryAdjustmentCreate, InventoryAdjustmentUpdate]):
    """
    Repository for managing InventoryAdjustment proposal records.
    """
    def __init__(self):
        super().__init__(InventoryAdjustment)


inventory_transaction_type_repository = InventoryTransactionTypeRepository()
stock_ledger_repository = StockLedgerRepository()
stock_balance_repository = StockBalanceRepository()
opening_stock_repository = OpeningStockRepository()
inventory_adjustment_repository = InventoryAdjustmentRepository()
