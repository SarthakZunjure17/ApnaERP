import uuid
from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.base import BaseSchema, TimestampSchema, UUIDSchema


class FileCreate(BaseModel):
    """
    Schema for creating a File record in database.
    """
    original_filename: str
    stored_filename: str
    file_extension: str
    mime_type: str
    file_size: int
    storage_path: str
    uploaded_by_id: uuid.UUID
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    checksum: str
    is_public: bool = False


class FileResponse(UUIDSchema, TimestampSchema):
    """
    Output schema for file metadata (strictly conceals internal storage_path).
    """
    original_filename: str
    stored_filename: str
    file_extension: str
    mime_type: str
    file_size: int
    uploaded_by_id: uuid.UUID
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    checksum: str
    is_public: bool
