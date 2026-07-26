from fastapi import APIRouter, status
from app.core.config import settings
from app.schemas.health import RootResponse

router = APIRouter()


@router.get(
    "/",
    response_model=RootResponse,
    status_code=status.HTTP_200_OK,
    summary="Root API Endpoint",
    description="Welcome root endpoint returning API information and documentation link.",
    tags=["System Diagnostics"]
)
async def get_root() -> RootResponse:
    """
    Root endpoint for ApnaERP API.
    """
    return RootResponse(
        message=f"Welcome to {settings.PROJECT_NAME} Backend API",
        app_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        docs_url="/docs"
    )
