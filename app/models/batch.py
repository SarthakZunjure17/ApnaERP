from datetime import datetime, timezone
import uuid
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class Batch(Base, UUIDMixin, TimestampMixin):
    """
    Batch ORM Model.
    Tracks production or supplier batch lots with manufacturing and expiry dates.
    Status: Active, Expired, Consumed.
    """
    __tablename__ = "batches"

    batch_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique identifier for the product batch",
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Reference to Product master record",
    )
    manufacturing_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Batch manufacturing date",
    )
    expiry_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Batch expiration date",
    )
    supplier_batch_ref: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="External supplier batch reference number",
    )
    current_quantity: Mapped[float] = mapped_column(
        Numeric(18, 4),
        default=0.0,
        nullable=False,
        comment="Current physical quantity remaining in this batch",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="Active",
        nullable=False,
        index=True,
        comment="Batch status: Active, Expired, Consumed",
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Batch(id={self.id}, batch_number='{self.batch_number}', product_id={self.product_id}, status='{self.status}')>"
