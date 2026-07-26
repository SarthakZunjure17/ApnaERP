from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """
    Schema for system health check endpoint response.
    """
    status: str = Field(default="healthy", description="System health status")
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Running environment")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC Timestamp of health check")
    components: Optional[Dict[str, Any]] = Field(default=None, description="Detailed component statuses")


class DatabaseHealthResponse(BaseModel):
    """
    Schema for database connectivity health check response.
    """
    status: str = Field(..., description="Database connectivity status ('connected' | 'disconnected')")
    latency_ms: Optional[float] = Field(default=None, description="Query execution latency in milliseconds")
    database: Optional[str] = Field(default=None, description="Database name")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC Timestamp")
    error: Optional[str] = Field(default=None, description="Error message if disconnected")


class RootResponse(BaseModel):
    """
    Schema for root endpoint response.
    """
    message: str = Field(..., description="Welcome message")
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")
    docs_url: str = Field(..., description="API Documentation URL")
