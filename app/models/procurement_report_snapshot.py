from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional
from sqlalchemy import DateTime, Integer, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class ProcurementReportSnapshot(Base, UUIDMixin, TimestampMixin):
    """
    ProcurementReportSnapshot ORM model.
    Periodic telemetry snapshot storing purchase spend, open PO counts, vendor performance, and department metrics.
    """
    __tablename__ = "procurement_report_snapshots"

    snapshot_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
        comment="Timestamp when procurement snapshot was computed",
    )
    total_purchase_spend: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        default=Decimal("0.0"),
        nullable=False,
        comment="Total procurement purchasing spend value",
    )
    open_po_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Total count of active/open Purchase Orders",
    )
    open_requisitions_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Total count of active/pending Purchase Requisitions",
    )
    active_suppliers_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Total count of active suppliers",
    )
    delayed_orders_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Total count of overdue Purchase Orders",
    )
    metrics_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Detailed breakdown metrics (top spenders, spend by department, category breakdown)",
    )

    def __repr__(self) -> str:
        return f"<ProcurementReportSnapshot(snapshot_date={self.snapshot_date}, spend={self.total_purchase_spend})>"
