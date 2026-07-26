import uuid
from contextvars import ContextVar
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
client_ip_var: ContextVar[Optional[str]] = ContextVar("client_ip", default=None)
user_agent_var: ContextVar[Optional[str]] = ContextVar("user_agent", default=None)
http_method_var: ContextVar[Optional[str]] = ContextVar("http_method", default=None)
api_endpoint_var: ContextVar[Optional[str]] = ContextVar("api_endpoint", default=None)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware that generates a unique correlation X-Request-ID header per HTTP request
    and attaches request context metadata to contextvars for audit logging.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        # Extract client IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            ip_address = forwarded_for.split(",")[0].strip()
        elif request.client:
            ip_address = request.client.host
        else:
            ip_address = "unknown"

        user_agent = request.headers.get("User-Agent", "unknown")
        method = request.method
        endpoint = request.url.path

        # Set context variables for thread/async safety
        token_req = request_id_var.set(request_id)
        token_ip = client_ip_var.set(ip_address)
        token_ua = user_agent_var.set(user_agent)
        token_method = http_method_var.set(method)
        token_ep = api_endpoint_var.set(endpoint)

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            request_id_var.reset(token_req)
            client_ip_var.reset(token_ip)
            user_agent_var.reset(token_ua)
            http_method_var.reset(token_method)
            api_endpoint_var.reset(token_ep)
