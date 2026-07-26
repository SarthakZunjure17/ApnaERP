from typing import Optional
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDMixin


class Permission(Base, UUIDMixin, TimestampMixin):
    """
    Permission ORM Model representing granular system action authorization rights.
    """
    __tablename__ = "permissions"

    name: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        nullable=False,
        comment="Human readable permission name (e.g. Create Users)",
    )
    code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique permission code (e.g. users.create, admin.full_access)",
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Detailed description of permission action",
    )
    module_name: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
        comment="Target ERP module name (e.g. users, hr, inventory, sales, admin)",
    )

    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, code='{self.code}', module='{self.module_name}')>"
