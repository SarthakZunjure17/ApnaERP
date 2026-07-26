from typing import Any
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# PostgreSQL Naming Convention for clean Alembic constraint names
POSTGRES_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """
    Base Declarative class for all SQLAlchemy 2.0 ORM models in ApnaERP.
    Applies strict, standardized constraint naming conventions for seamless Alembic migrations.
    """
    metadata = MetaData(naming_convention=POSTGRES_NAMING_CONVENTION)

    # Utility method to represent model instances as dicts
    def to_dict(self) -> dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
