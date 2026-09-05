from datetime import datetime, timezone
import uuid
from typing import List, Optional
from sqlalchemy import DateTime, ForeignKey, JSON, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class GoodsIssue(Base, UUIDMixin, TimestampMixin):
    """
    GoodsIssue ORM model.
    Represents outgoing physical stock documents (e.g. for consumption, internal usage, damage, sampling, etc.).
    Lifecycle states: Draft -> Approved -> Issued (or Cancelled).
    Issuing/Executing a GoodsIssue validates negative stock limits and generates immutable StockLedger OUT entries.
    """
    __tablename__ = "goods_issues"

    issue_number: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique goods issue document number",
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Source warehouse facility",
    )
    issue_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Effective date and time of physical issue (UTC)",
    )
    issue_reason: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Issue reason: Consumption, Internal, Damage, Sample, Adjustment, Other",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="Draft",
        nullable=False,
        index=True,
        comment="Document status: Draft, Issued, Cancelled",
    )
    remarks: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Remarks or issue justification notes",
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ID who created the issue document",
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ID who approved or executed the issue document",
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when document was approved/issued (UTC)",
    )

    # Relationships
    warehouse: Mapped["Warehouse"] = relationship("Warehouse", lazy="selectin")
    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by], lazy="selectin")
    approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by], lazy="selectin")
    items: Mapped[List["GoodsIssueItem"]] = relationship(
        "GoodsIssueItem", back_populates="goods_issue", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def notes(self) -> Optional[str]:
        return self.remarks

    @notes.setter
    def notes(self, val: Optional[str]):
        self.remarks = val

    @property
    def issued_by(self) -> Optional[uuid.UUID]:
        return self.approved_by

    @issued_by.setter
    def issued_by(self, val: Optional[uuid.UUID]):
        self.approved_by = val

    def __repr__(self) -> str:
        return f"<GoodsIssue(id={self.id}, number='{self.issue_number}', status='{self.status}')>"


class GoodsIssueItem(Base, UUIDMixin):
    """
    GoodsIssueItem ORM model.
    Line items associated with a GoodsIssue document.
    """
    __tablename__ = "goods_issue_items"

    goods_issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("goods_issues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent GoodsIssue document reference",
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Reference to Product master record",
    )
    storage_location_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("storage_locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Source storage location within warehouse",
    )
    quantity: Mapped[float] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="Issued stock quantity",
    )
    unit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("unit_of_measures.id", ondelete="SET NULL"),
        nullable=True,
        comment="Unit of Measure for issued quantity",
    )
    batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("batches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional source batch ID",
    )
    serial_numbers: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
        comment="List of serial numbers for serialized item issues",
    )
    reservation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stock_reservations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional associated StockReservation ID being consumed",
    )
    remarks: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Line item remarks",
    )

    # Relationships
    goods_issue: Mapped["GoodsIssue"] = relationship("GoodsIssue", back_populates="items")
    product: Mapped["Product"] = relationship("Product", lazy="selectin")
    storage_location: Mapped[Optional["StorageLocation"]] = relationship("StorageLocation", lazy="selectin")
    unit: Mapped[Optional["UnitOfMeasure"]] = relationship("UnitOfMeasure", lazy="selectin")
    batch: Mapped[Optional["Batch"]] = relationship("Batch", lazy="selectin")
    reservation: Mapped[Optional["StockReservation"]] = relationship("StockReservation", lazy="selectin")

    @property
    def notes(self) -> Optional[str]:
        return self.remarks

    @notes.setter
    def notes(self, val: Optional[str]):
        self.remarks = val

    def __repr__(self) -> str:
        return f"<GoodsIssueItem(id={self.id}, product_id={self.product_id}, qty={self.quantity})>"
