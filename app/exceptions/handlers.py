import logging
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from app.exceptions.base import ApnaERPException
from app.schemas.responses import ErrorDetail, ErrorResponse, create_error_response

logger = logging.getLogger("app.exceptions")


async def apnaerp_exception_handler(request: Request, exc: ApnaERPException) -> JSONResponse:
    """
    Handler for custom domain ApnaERPException instances.
    """
    logger.warning(f"ApnaERPException on [{request.method} {request.url.path}]: {exc.message} (Code: {exc.error_code})")
    error_res = create_error_response(
        message=exc.message,
        error_code=exc.error_code,
        details=exc.details,
    )
    return JSONResponse(status_code=exc.status_code, content=error_res.model_dump())


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handler for standard FastAPI/Starlette HTTPException instances.
    """
    logger.warning(f"HTTPException on [{request.method} {request.url.path}]: {exc.detail} (Status: {exc.status_code})")
    error_code = "HTTP_ERROR"
    if exc.status_code == 401:
        error_code = "UNAUTHORIZED"
    elif exc.status_code == 403:
        error_code = "FORBIDDEN"
    elif exc.status_code == 404:
        error_code = "NOT_FOUND"

    error_res = create_error_response(
        message=str(exc.detail),
        error_code=error_code,
    )
    return JSONResponse(status_code=exc.status_code, content=error_res.model_dump())


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handler for FastAPI Pydantic request validation errors.
    """
    logger.warning(f"Validation error on [{request.method} {request.url.path}]: {exc.errors()}")
    details = []
    for err in exc.errors():
        field = ".".join(str(loc) for loc in err.get("loc", []))
        msg = err.get("msg", "Invalid input value")
        details.append(ErrorDetail(field=field, message=msg))

    error_res = create_error_response(
        message="Request payload validation failed.",
        error_code="VALIDATION_ERROR",
        details=details,
    )
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=error_res.model_dump())


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """
    Handler for unhandled database errors.
    """
    logger.error(f"Database error on [{request.method} {request.url.path}]: {exc}", exc_info=True)
    error_res = create_error_response(
        message="A database processing error occurred.",
        error_code="DATABASE_ERROR",
    )
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=error_res.model_dump())


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all handler for unhandled internal server exceptions.
    """
    logger.error(f"Unhandled exception on [{request.method} {request.url.path}]: {exc}", exc_info=True)
    error_res = create_error_response(
        message="An unexpected internal server error occurred.",
        error_code="INTERNAL_SERVER_ERROR",
    )
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=error_res.model_dump())


def register_exception_handlers(app: FastAPI) -> None:
    """
    Registers exception handlers onto the FastAPI application.
    """
    app.add_exception_handler(ApnaERPException, apnaerp_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
