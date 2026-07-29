import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class CountryCreate(BaseModel):
    """
    Schema for creating a new Country record.
    """
    code: str = Field(..., max_length=10, description="ISO country code (e.g. IND, USA, GBR)")
    name: str = Field(..., max_length=100, description="Country full name")
    currency: str = Field(..., max_length=10, description="Default currency code (e.g. INR, USD, GBP)")
    is_active: bool = Field(True, description="Active status flag")


class CountryUpdate(BaseModel):
    """
    Schema for updating an existing Country record.
    """
    name: Optional[str] = Field(None, max_length=100)
    currency: Optional[str] = Field(None, max_length=10)
    is_active: Optional[bool] = None


class CountryResponse(BaseModel):
    """
    Response schema for a Country.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    currency: str
    is_active: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime
