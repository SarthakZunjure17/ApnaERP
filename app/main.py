from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1.api import api_router
from app.api.v1.endpoints import audit, auth, health, rbac, root
from app.core.config import settings
from app.core.events import lifespan
from app.core.logging import setup_logging
from app.exceptions.handlers import register_exception_handlers
from app.middleware.logging_middleware import RequestLoggingMiddleware
from app.middleware.request_context import RequestContextMiddleware

# Initialize structured logging configuration
setup_logging()

# Create FastAPI application instance with metadata
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-Grade Backend API for ApnaERP System",
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Register Exception Handlers
register_exception_handlers(app)

# Set up CORS Middleware
if settings.ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.ALLOWED_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Set up Request Context & X-Request-ID Middleware
app.add_middleware(RequestContextMiddleware)

# Set up Request Timing & Logging Middleware
app.add_middleware(RequestLoggingMiddleware)

# Prometheus Metrics Instrumentation
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# Register Root, Health, Auth, RBAC, and Audit endpoints at top-level
app.include_router(root.router)
app.include_router(health.router)
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(rbac.router, prefix="", tags=["Role-Based Access Control"])
app.include_router(audit.router, prefix="", tags=["Audit Logging"])

# Register API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
