import uuid
from typing import List, Optional
from sqlalchemy import ForeignKey, String, func, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class RolePermission(Base):
    """
    Association table representing Many-to-Many relationship between Roles and Permissions.
    """
    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Role(Base, UUIDMixin, TimestampMixin):
    """
    Role ORM Model representing security authority levels.
    """
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique role title (e.g. Super Admin, HR Manager)",
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Detailed role description",
    )

    # Relationships
    permissions: Mapped[List["Permission"]] = relationship(
        "Permission",
        secondary="role_permissions",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name='{self.name}')>"
