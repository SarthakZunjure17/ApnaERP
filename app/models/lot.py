import uuid
from typing import Any, Dict, Optional
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class Lot(Base, UUIDMixin, TimestampMixin):
    """
    Lot ORM Model.
    Production or supplier lot entity for inventory grouping and full movement traceability.
    """
    __tablename__ = "lots"

    lot_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique lot identification code",
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Reference to Product master record",
    )
    production_lot: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Internal production run/lot code",
    )
    supplier_lot: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Supplier-provided lot code",
    )
    traceability_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Extended lineage, QA test results, or certificate metadata",
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Lot(id={self.id}, lot_number='{self.lot_number}', product_id={self.product_id})>"
