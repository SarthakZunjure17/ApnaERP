from typing import Any, List, Optional
from app.schemas.responses import ErrorDetail


class ApnaERPException(Exception):
    """
    Base domain exception for ApnaERP system.
    """
    def __init__(
        self,
        message: str = "An unexpected application error occurred.",
        status_code: int = 500,
        error_code: str = "INTERNAL_SERVER_ERROR",
        details: Optional[List[ErrorDetail]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details
        super().__init__(self.message)


class NotFoundException(ApnaERPException):
    """
    Exception raised when a requested database resource or entity is not found.
    """
    def __init__(self, message: str = "Requested resource not found.", details: Optional[List[ErrorDetail]] = None):
        super().__init__(
            message=message,
            status_code=404,
            error_code="RESOURCE_NOT_FOUND",
            details=details,
        )


class ValidationException(ApnaERPException):
    """
    Exception raised when domain validation rules fail.
    """
    def __init__(self, message: str = "Validation failed.", details: Optional[List[ErrorDetail]] = None):
        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class DuplicateResourceException(ApnaERPException):
    """
    Exception raised when attempting to create a duplicate unique entity.
    """
    def __init__(self, message: str = "Resource already exists.", details: Optional[List[ErrorDetail]] = None):
        super().__init__(
            message=message,
            status_code=400,
            error_code="DUPLICATE_RESOURCE",
            details=details,
        )


class UnauthorizedException(ApnaERPException):
    """
    Exception raised when authentication is missing or invalid.
    """
    def __init__(self, message: str = "Authentication credentials were missing or invalid.", details: Optional[List[ErrorDetail]] = None):
        super().__init__(
            message=message,
            status_code=401,
            error_code="UNAUTHORIZED",
            details=details,
        )


class ForbiddenException(ApnaERPException):
    """
    Exception raised when the user lacks required permission or role.
    """
    def __init__(self, message: str = "Permission denied for the requested resource.", details: Optional[List[ErrorDetail]] = None):
        super().__init__(
            message=message,
            status_code=403,
            error_code="FORBIDDEN",
            details=details,
        )


class DatabaseException(ApnaERPException):
    """
    Exception raised when an underlying database interaction fails.
    """
    def __init__(self, message: str = "Database operation failed.", details: Optional[List[ErrorDetail]] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_code="DATABASE_ERROR",
            details=details,
        )
