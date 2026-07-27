from fastapi import APIRouter
from app.api.v1.endpoints import (
    approval,
    attendance,
    audit,
    auth,
    departments,
    employee_documents,
    employees,
    files,
    health,
    holidays,
    hr_configurations,
    leave_type,
    leave_balance,
    leave_request,
    notifications,
    positions,
    rbac,
    root,
    shift_assignment,
    shifts,
    templates,
)

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
api_router.include_router(employee_documents.router, prefix="", tags=["Employee Document Management"])
api_router.include_router(positions.router, prefix="", tags=["Position Management"])
api_router.include_router(hr_configurations.router, prefix="", tags=["HR Configuration & Policies"])
api_router.include_router(shifts.router, prefix="/shifts", tags=["Shift Management"])
api_router.include_router(shift_assignment.router, prefix="/shift-assignments", tags=["Shift Assignment & Scheduling"])
api_router.include_router(holidays.router, prefix="/holidays", tags=["Holiday Calendar"])
api_router.include_router(attendance.router, prefix="/attendance", tags=["Enterprise Attendance Engine"])
api_router.include_router(leave_type.router, prefix="/leave-types", tags=["Enterprise Leave Types & Policies"])
api_router.include_router(leave_balance.router, prefix="/leave-balances", tags=["Enterprise Leave Balance Management"])
api_router.include_router(leave_request.router, prefix="/leave-requests", tags=["Enterprise Leave Request Workflow"])
api_router.include_router(approval.router, prefix="", tags=["Enterprise Approval Engine"])
