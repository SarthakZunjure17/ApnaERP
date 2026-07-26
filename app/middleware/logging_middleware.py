import logging
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("app.middleware")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs incoming HTTP requests and processing duration.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        path = request.url.path
        method = request.method
        
        logger.info(f"Incoming Request: {method} {path}")
        
        try:
            response = await call_next(request)
            process_time = (time.time() - start_time) * 1000
            response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
            logger.info(
                f"Completed Request: {method} {path} - Status: {response.status_code} - Process Time: {process_time:.2f}ms"
            )
            return response
        except Exception as exc:
            process_time = (time.time() - start_time) * 1000
            logger.error(
                f"Unhandled Exception for Request: {method} {path} - Process Time: {process_time:.2f}ms - Error: {exc}",
                exc_info=True,
            )
            raise exc
