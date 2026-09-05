from typing import Optional
import uuid
from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class InventoryPolicy(Base, UUIDMixin, TimestampMixin):
    """
    InventoryPolicy ORM model representing inventory behavioral configurations.
    Defines valuation defaults, costing rules, negative stock allowances, and reservation policies.
    Provides canonical configuration foundation for downstream stock accounting and valuation engines.
    """
    __tablename__ = "inventory_policies"
    __table_args__ = (
        UniqueConstraint("warehouse_id", name="uq_inventory_policy_warehouse"),
    )

    warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Target Warehouse for facility-specific policy, or NULL for enterprise global policy",
    )
    valuation_method: Mapped[str] = mapped_column(
        String(50),
        default="FIFO",
        nullable=False,
        comment="Inventory valuation method: FIFO, LIFO, WEIGHTED_AVERAGE, STANDARD",
    )
    costing_method: Mapped[str] = mapped_column(
        String(50),
        default="STANDARD",
        nullable=False,
        comment="Costing strategy: STANDARD, ACTUAL, MOVING_AVERAGE",
    )
    negative_stock_allowed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Policy flag permitting negative balances during outbound issues",
    )
    default_reorder_strategy: Mapped[str] = mapped_column(
        String(50),
        default="MIN_MAX",
        nullable=False,
        comment="Replenishment strategy: MIN_MAX, FIXED_ORDER_QTY, PERIODIC",
    )
    default_reservation_behavior: Mapped[str] = mapped_column(
        String(50),
        default="STRICT",
        nullable=False,
        comment="Stock reservation behavior: STRICT, SOFT, MANUAL",
    )
    low_stock_alert_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Flag triggering system alerts when items breach reorder levels",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Active policy status flag",
    )

    # Relationships
    warehouse: Mapped[Optional["Warehouse"]] = relationship(
        "Warehouse",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<InventoryPolicy(warehouse_id='{self.warehouse_id}', valuation='{self.valuation_method}', is_active={self.is_active})>"
