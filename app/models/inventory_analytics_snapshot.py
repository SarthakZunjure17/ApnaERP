from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import DateTime, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import UUIDMixin


class InventoryAnalyticsSnapshot(Base, UUIDMixin):
    """
    InventoryAnalyticsSnapshot ORM Model.
    Periodic snapshot table for high-level inventory metrics, turnover, valuation, and utilization.
    """
    __tablename__ = "inventory_analytics_snapshots"

    snapshot_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
        comment="Snapshot timestamp (UTC)",
    )
    total_inventory_value: Mapped[float] = mapped_column(
        Numeric(18, 4),
        default=0.0,
        nullable=False,
        comment="Aggregated monetary valuation of all stored stock",
    )
    total_items_count: Mapped[float] = mapped_column(
        Numeric(18, 4),
        default=0.0,
        nullable=False,
        comment="Total physical stock units held across warehouses",
    )
    turnover_ratio: Mapped[float] = mapped_column(
        Numeric(10, 4),
        default=0.0,
        nullable=False,
        comment="Calculated inventory turnover ratio",
    )
    warehouse_utilization_pct: Mapped[float] = mapped_column(
        Numeric(5, 2),
        default=0.0,
        nullable=False,
        comment="Average warehouse capacity utilization percentage",
    )
    reserved_stock_qty: Mapped[float] = mapped_column(
        Numeric(18, 4),
        default=0.0,
        nullable=False,
        comment="Total stock units currently reserved",
    )
    available_stock_qty: Mapped[float] = mapped_column(
        Numeric(18, 4),
        default=0.0,
        nullable=False,
        comment="Total unreserved stock units available for issue",
    )
    expiring_stock_qty: Mapped[float] = mapped_column(
        Numeric(18, 4),
        default=0.0,
        nullable=False,
        comment="Total stock units expiring within alert threshold window",
    )
    metrics_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Detailed breakdown metrics (by warehouse, category, top moving SKUs)",
    )

    def __repr__(self) -> str:
        return f"<InventoryAnalyticsSnapshot(id={self.id}, date={self.snapshot_date}, val={self.total_inventory_value}, items={self.total_items_count})>"
