import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.base import BaseSchema, TimestampSchema, UUIDSchema


class AuditLogCreate(BaseModel):
    """
    Schema for creating an audit log entry.
    """
    user_id: Optional[uuid.UUID] = None
    username: Optional[str] = None
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    previous_data: Optional[Dict[str, Any]] = None
    new_data: Optional[Dict[str, Any]] = None
    http_method: Optional[str] = None
    api_endpoint: Optional[str] = None
    request_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    status_code: Optional[int] = None


class AuditLogResponse(UUIDSchema, TimestampSchema):
    """
    Schema for returning audit log details.
    """
    user_id: Optional[uuid.UUID] = None
    username: Optional[str] = None
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    previous_data: Optional[Dict[str, Any]] = None
    new_data: Optional[Dict[str, Any]] = None
    http_method: Optional[str] = None
    api_endpoint: Optional[str] = None
    request_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    status_code: Optional[int] = None
