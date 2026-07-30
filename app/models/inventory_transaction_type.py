from typing import Optional
from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class InventoryTransactionType(Base, UUIDMixin, TimestampMixin):
    """
    InventoryTransactionType ORM model.
    Defines transaction classification types (e.g. OPENING_STOCK, PURCHASE_RECEIPT, SALES_ISSUE, etc.)
    and their net direction impact (IN, OUT, TRANSFER, ADJUSTMENT, SYSTEM).
    """
    __tablename__ = "inventory_transaction_types"

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique transaction type code (e.g., OPENING_STOCK)",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Human-readable transaction type name",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed description of transaction type usage",
    )
    direction: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Inventory movement direction: IN, OUT, TRANSFER, ADJUSTMENT, SYSTEM",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Active transaction type status flag",
    )

    def __repr__(self) -> str:
        return f"<InventoryTransactionType(code='{self.code}', direction='{self.direction}')>"
