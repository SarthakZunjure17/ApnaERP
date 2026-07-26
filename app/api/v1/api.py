from fastapi import APIRouter
from app.api.v1.endpoints import auth, health, rbac, root

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(root.router, prefix="", tags=["Root"])
api_router.include_router(health.router, prefix="", tags=["Health Check"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(rbac.router, prefix="", tags=["Role-Based Access Control"])
