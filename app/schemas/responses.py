from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field
from app.schemas.base import BaseSchema
from app.utils.pagination import PaginatedResult

T = TypeVar("T")


class SuccessResponse(BaseSchema, Generic[T]):
    """
    Standardized API success wrapper.
    """
    success: bool = Field(default=True, description="Indicates request success")
    message: str = Field(default="Operation completed successfully.", description="Human-readable response message")
    data: Optional[T] = Field(default=None, description="Response payload")


class ErrorDetail(BaseModel):
    """
    Detailed error payload.
    """
    field: Optional[str] = Field(default=None, description="Target field name for validation error")
    message: str = Field(description="Specific error detail message")


class ErrorResponse(BaseModel):
    """
    Standardized API error wrapper.
    """
    success: bool = Field(default=False, description="Indicates request failure")
    message: str = Field(description="Primary error message summary")
    detail: Optional[str] = Field(default=None, description="FastAPI backward-compatible detail field")
    error_code: str = Field(description="Machine-readable error classification code")
    details: Optional[List[ErrorDetail]] = Field(default=None, description="Detailed list of validation or field errors")


class PaginatedResponse(BaseSchema, Generic[T]):
    """
    Standardized API paginated response wrapper.
    """
    success: bool = Field(default=True, description="Indicates request success")
    message: str = Field(default="Paginated records retrieved successfully.", description="Response message")
    data: List[T] = Field(default_factory=list, description="Page item records")
    total: int = Field(description="Total number of matching records in database")
    page: int = Field(description="Current page number (1-indexed)")
    page_size: int = Field(description="Number of item records per page")
    total_pages: int = Field(description="Total calculated pages available")
    has_next: bool = Field(description="True if subsequent page exists")
    has_prev: bool = Field(description="True if preceding page exists")


def create_success_response(data: Any = None, message: str = "Operation completed successfully.") -> SuccessResponse[Any]:
    """
    Helper function to build a standardized SuccessResponse.
    """
    return SuccessResponse(success=True, message=message, data=data)


def create_paginated_response(paginated_result: PaginatedResult[T], message: str = "Paginated records retrieved successfully.") -> PaginatedResponse[T]:
    """
    Helper function to build a standardized PaginatedResponse from a PaginatedResult.
    """
    return PaginatedResponse(
        success=True,
        message=message,
        data=paginated_result.items,
        total=paginated_result.total,
        page=paginated_result.page,
        page_size=paginated_result.page_size,
        total_pages=paginated_result.total_pages,
        has_next=paginated_result.has_next,
        has_prev=paginated_result.has_prev,
    )


def create_error_response(message: str, error_code: str = "INTERNAL_ERROR", details: Optional[List[ErrorDetail]] = None) -> ErrorResponse:
    """
    Helper function to build a standardized ErrorResponse.
    """
    return ErrorResponse(
        success=False,
        message=message,
        detail=message,
        error_code=error_code,
        details=details,
    )
