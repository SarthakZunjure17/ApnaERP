from datetime import datetime, timezone
from decimal import Decimal
import uuid
from typing import Optional
from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class SalesReportSnapshot(Base, UUIDMixin, TimestampMixin):
    """
    SalesReportSnapshot ORM model.
    Stores pre-calculated analytics snapshots for revenue summaries, sales trends, top customers, and top products.
    """
    __tablename__ = "sales_report_snapshots"

    snapshot_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
        comment="Snapshot aggregation date (UTC)",
    )
    period_type: Mapped[str] = mapped_column(
        String(20),
        default="Daily",
        nullable=False,
        index=True,
        comment="Aggregation period: Daily, Weekly, Monthly",
    )
    total_revenue: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Total net revenue during period",
    )
    total_orders: Mapped[int] = mapped_column(
        Numeric(10, 0),
        default=0,
        nullable=False,
        comment="Total sales orders completed during period",
    )
    avg_order_value: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Average order value during period",
    )
    metrics_json: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Detailed metrics JSON breakdown (top customers, top products, warehouse sales, etc.)",
    )
