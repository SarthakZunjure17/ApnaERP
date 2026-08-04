from datetime import datetime, timezone
import uuid
from typing import List, Optional
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class RFQ(Base, UUIDMixin, TimestampMixin):
    """
    RFQ (Request For Quotation) ORM model.
    Sourcing document issued to multiple suppliers soliciting commercial bids/quotations.
    Lifecycle states: Draft -> Issued -> Closed (or Cancelled).
    """
    __tablename__ = "rfqs"

    rfq_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique RFQ tracking number (e.g. RFQ-2026-00001)",
    )
    title: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        comment="Short descriptive title of RFQ",
    )
    requisition_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_requisitions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional source PurchaseRequisition FK",
    )
    submission_deadline: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Closing date/time for supplier quotation submissions",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="Draft",
        nullable=False,
        index=True,
        comment="Status: Draft, Issued, Closed, Cancelled",
    )
    terms_and_conditions: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Sourcing terms and delivery requirements",
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Internal sourcing notes",
    )

    # Relationships
    requisition: Mapped[Optional["PurchaseRequisition"]] = relationship("PurchaseRequisition", lazy="selectin")
    invited_suppliers: Mapped[List["RFQSupplier"]] = relationship(
        "RFQSupplier", back_populates="rfq", cascade="all, delete-orphan", lazy="selectin"
    )
    quotations: Mapped[List["SupplierQuotation"]] = relationship("SupplierQuotation", back_populates="rfq", lazy="selectin")

    def __repr__(self) -> str:
        return f"<RFQ(number='{self.rfq_number}', title='{self.title}', status='{self.status}')>"


class RFQSupplier(Base, UUIDMixin, TimestampMixin):
    """
    RFQSupplier ORM model.
    Junction table representing suppliers invited to participate in an RFQ.
    """
    __tablename__ = "rfq_suppliers"

    rfq_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rfqs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to parent RFQ",
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to invited Supplier",
    )
    invited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Timestamp when supplier was invited",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="Invited",
        nullable=False,
        index=True,
        comment="Invitation status: Invited, Quoted, Declined",
    )

    # Relationships
    rfq: Mapped["RFQ"] = relationship("RFQ", back_populates="invited_suppliers")
    supplier: Mapped["Supplier"] = relationship("Supplier", lazy="selectin")

    def __repr__(self) -> str:
        return f"<RFQSupplier(rfq_id='{self.rfq_id}', supplier_id='{self.supplier_id}', status='{self.status}')>"
