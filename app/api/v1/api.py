from fastapi import APIRouter
from app.api.v1.endpoints import audit, auth, departments, employees, files, health, notifications, rbac, root, templates

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(root.router, prefix="", tags=["Root"])
api_router.include_router(health.router, prefix="", tags=["Health Check"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(rbac.router, prefix="", tags=["Role-Based Access Control"])
api_router.include_router(audit.router, prefix="", tags=["Audit Logging"])
api_router.include_router(files.router, prefix="", tags=["File & Document Management"])
api_router.include_router(notifications.router, prefix="", tags=["Notification System"])
api_router.include_router(templates.router, prefix="", tags=["Notification Templates"])
api_router.include_router(departments.router, prefix="/departments", tags=["Department Management"])
api_router.include_router(employees.router, prefix="/employees", tags=["Employee Management"])
