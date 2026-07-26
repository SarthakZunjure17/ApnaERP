import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """
    Base Pydantic v2 schema configured with ORM mode compatibility.
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class UUIDSchema(BaseSchema):
    """
    Schema mixin providing UUID v4 primary key.
    """
    id: uuid.UUID


class TimestampSchema(BaseSchema):
    """
    Schema mixin providing record creation and update timestamps.
    """
    created_at: datetime
    updated_at: datetime


class SoftDeleteSchema(BaseSchema):
    """
    Schema mixin providing soft deletion flag and deletion timestamp.
    """
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
