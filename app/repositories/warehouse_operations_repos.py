from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.goods_issue import GoodsIssue, GoodsIssueItem
from app.models.goods_receipt import GoodsReceipt, GoodsReceiptItem
from app.models.stock_transfer import StockTransfer, StockTransferItem
from app.repositories.base import BaseRepository
from app.schemas.warehouse_operations import (
    GoodsIssueCreate,
    GoodsIssueUpdate,
    GoodsReceiptCreate,
    GoodsReceiptUpdate,
    StockTransferCreate,
    StockTransferUpdate,
)


class GoodsReceiptRepository(BaseRepository[GoodsReceipt, GoodsReceiptCreate, GoodsReceiptUpdate]):
    """
    Repository for managing GoodsReceipt documents and items.
    """
    def __init__(self):
        super().__init__(GoodsReceipt)

    async def exists_by_number(self, db: AsyncSession, receipt_number: str) -> bool:
        result = await db.execute(
            select(func.count(GoodsReceipt.id)).where(func.upper(GoodsReceipt.receipt_number) == receipt_number.upper())
        )
        return (result.scalar() or 0) > 0

    async def get_max_number_suffix(self, db: AsyncSession, prefix: str) -> int:
        stmt = select(GoodsReceipt.receipt_number).where(GoodsReceipt.receipt_number.like(f"{prefix}%"))
        result = await db.execute(stmt)
        numbers = result.scalars().all()
        max_val = 0
        for num in numbers:
            try:
                suffix = int(num.split("-")[-1])
                if suffix > max_val:
                    max_val = suffix
            except (ValueError, IndexError):
                continue
        return max_val


    async def get_goods_receipts_paginated(
        self,
        db: AsyncSession,
        warehouse_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        search_term: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[GoodsReceipt], int]:
        stmt = select(GoodsReceipt)
        count_stmt = select(func.count(GoodsReceipt.id))

        filters = []
        if warehouse_id:
            filters.append(GoodsReceipt.warehouse_id == warehouse_id)
        if status:
            filters.append(func.lower(GoodsReceipt.status) == status.lower())
        if start_date:
            filters.append(GoodsReceipt.receipt_date >= start_date)
        if end_date:
            filters.append(GoodsReceipt.receipt_date <= end_date)

        if search_term:
            pattern = f"%{search_term}%"
            filters.append(
                or_(
                    GoodsReceipt.receipt_number.ilike(pattern),
                    GoodsReceipt.supplier_reference.ilike(pattern),
                    GoodsReceipt.external_reference.ilike(pattern),
                    GoodsReceipt.remarks.ilike(pattern),
                )
            )

        if filters:
            stmt = stmt.where(and_(*filters))
            count_stmt = count_stmt.where(and_(*filters))

        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(GoodsReceipt.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all()), total


class GoodsIssueRepository(BaseRepository[GoodsIssue, GoodsIssueCreate, GoodsIssueUpdate]):
    """
    Repository for managing GoodsIssue documents and items.
    """
    def __init__(self):
        super().__init__(GoodsIssue)

    async def exists_by_number(self, db: AsyncSession, issue_number: str) -> bool:
        result = await db.execute(
            select(func.count(GoodsIssue.id)).where(func.upper(GoodsIssue.issue_number) == issue_number.upper())
        )
        return (result.scalar() or 0) > 0

    async def get_goods_issues_paginated(
        self,
        db: AsyncSession,
        warehouse_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        issue_reason: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        search_term: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[GoodsIssue], int]:
        stmt = select(GoodsIssue)
        count_stmt = select(func.count(GoodsIssue.id))

        filters = []
        if warehouse_id:
            filters.append(GoodsIssue.warehouse_id == warehouse_id)
        if status:
            filters.append(func.lower(GoodsIssue.status) == status.lower())
        if issue_reason:
            filters.append(func.lower(GoodsIssue.issue_reason) == issue_reason.lower())
        if start_date:
            filters.append(GoodsIssue.issue_date >= start_date)
        if end_date:
            filters.append(GoodsIssue.issue_date <= end_date)

        if search_term:
            pattern = f"%{search_term}%"
            filters.append(
                or_(
                    GoodsIssue.issue_number.ilike(pattern),
                    GoodsIssue.issue_reason.ilike(pattern),
                    GoodsIssue.remarks.ilike(pattern),
                )
            )

        if filters:
            stmt = stmt.where(and_(*filters))
            count_stmt = count_stmt.where(and_(*filters))

        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(GoodsIssue.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all()), total


class StockTransferRepository(BaseRepository[StockTransfer, StockTransferCreate, StockTransferUpdate]):
    """
    Repository for managing StockTransfer documents and items.
    """
    def __init__(self):
        super().__init__(StockTransfer)

    async def exists_by_number(self, db: AsyncSession, transfer_number: str) -> bool:
        result = await db.execute(
            select(func.count(StockTransfer.id)).where(func.upper(StockTransfer.transfer_number) == transfer_number.upper())
        )
        return (result.scalar() or 0) > 0

    async def get_stock_transfers_paginated(
        self,
        db: AsyncSession,
        source_warehouse_id: Optional[uuid.UUID] = None,
        destination_warehouse_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        search_term: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[StockTransfer], int]:
        stmt = select(StockTransfer)
        count_stmt = select(func.count(StockTransfer.id))

        filters = []
        if source_warehouse_id:
            filters.append(StockTransfer.source_warehouse_id == source_warehouse_id)
        if destination_warehouse_id:
            filters.append(StockTransfer.destination_warehouse_id == destination_warehouse_id)
        if status:
            filters.append(func.lower(StockTransfer.status) == status.lower())
        if start_date:
            filters.append(StockTransfer.transfer_date >= start_date)
        if end_date:
            filters.append(StockTransfer.transfer_date <= end_date)

        if search_term:
            pattern = f"%{search_term}%"
            filters.append(
                or_(
                    StockTransfer.transfer_number.ilike(pattern),
                    StockTransfer.remarks.ilike(pattern),
                )
            )

        if filters:
            stmt = stmt.where(and_(*filters))
            count_stmt = count_stmt.where(and_(*filters))

        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(StockTransfer.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all()), total


goods_receipt_repository = GoodsReceiptRepository()
goods_issue_repository = GoodsIssueRepository()
stock_transfer_repository = StockTransferRepository()
