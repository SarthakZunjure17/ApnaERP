from datetime import datetime, timezone
from decimal import Decimal
import uuid
from typing import List, Optional
from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class PurchaseRequisition(Base, UUIDMixin, TimestampMixin):
    """
    PurchaseRequisition ORM model.
    Internal demand request initiated by departments or employees prior to purchasing.
    Lifecycle states: Draft -> Submitted -> Approved (or Rejected/Cancelled) -> Partially Fulfilled -> Fulfilled.
    """
    __tablename__ = "purchase_requisitions"

    requisition_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique requisition tracking number (e.g. PR-2026-00001)",
    )
    requester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="User ID who initiated the purchase requisition",
    )
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Department ID requesting the materials",
    )
    required_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Target date by which materials are required",
    )
    priority: Mapped[str] = mapped_column(
        String(20),
        default="Medium",
        nullable=False,
        index=True,
        comment="Priority level: Low, Medium, High, Urgent",
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="Draft",
        nullable=False,
        index=True,
        comment="Status: Draft, Submitted, Approved, Rejected, Cancelled, Partially Fulfilled, Fulfilled",
    )
    total_estimated_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        default=Decimal("0.0"),
        nullable=False,
        comment="Aggregated estimated total cost of requisition",
    )
    remarks: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Business justification or requisition notes",
    )

    # Relationships
    requester: Mapped["User"] = relationship("User", lazy="selectin")
    department: Mapped[Optional["Department"]] = relationship("Department", lazy="selectin")
    items: Mapped[List["PurchaseRequisitionItem"]] = relationship(
        "PurchaseRequisitionItem", back_populates="requisition", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<PurchaseRequisition(number='{self.requisition_number}', status='{self.status}')>"


class PurchaseRequisitionItem(Base, UUIDMixin, TimestampMixin):
    """
    PurchaseRequisitionItem ORM model.
    Product line items included within a PurchaseRequisition.
    """
    __tablename__ = "purchase_requisition_items"

    requisition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_requisitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to parent PurchaseRequisition",
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="FK to requested Product",
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
        comment="Requested product quantity",
    )
    fulfilled_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        default=Decimal("0.0"),
        nullable=False,
        comment="Quantity converted to Purchase Order or fulfilled",
    )
    estimated_unit_price: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        default=Decimal("0.0"),
        nullable=False,
        comment="Estimated price per unit",
    )
    required_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Line item specific required date",
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="Pending",
        nullable=False,
        index=True,
        comment="Line status: Pending, Partially Fulfilled, Fulfilled, Cancelled",
    )

    # Relationships
    requisition: Mapped["PurchaseRequisition"] = relationship("PurchaseRequisition", back_populates="items")
    product: Mapped["Product"] = relationship("Product", lazy="selectin")

    def __repr__(self) -> str:
        return f"<PurchaseRequisitionItem(product_id='{self.product_id}', quantity={self.quantity})>"
