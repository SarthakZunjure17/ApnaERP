from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, has_permission
from app.models.approval_workflow import ApprovalHistory, ApprovalRequest, ApprovalWorkflow
from app.models.user import User
from app.schemas.approval_workflow import (
    ApprovalActionRequest,
    ApprovalHistoryResponse,
    ApprovalRequestCreate,
    ApprovalRequestListResponse,
    ApprovalRequestResponse,
    ApprovalStepResponse,
    ApprovalWorkflowCreate,
    ApprovalWorkflowListResponse,
    ApprovalWorkflowResponse,
    ApprovalWorkflowUpdate,
)
from app.services.approval_engine import ApprovalEngineService
from app.services.approval_workflow import ApprovalWorkflowService
from app.utils.filters import FilterCriterion
from app.utils.pagination import PaginationParams

router = APIRouter()


def _format_workflow_response(item: ApprovalWorkflow) -> ApprovalWorkflowResponse:
    """Helper formatting ApprovalWorkflow ORM entity to response schema."""
    try:
        formatted_steps = []
        if item.steps:
            for s in item.steps:
                if getattr(s, "is_deleted", False):
                    continue
                role_name = s.approver_role.name if getattr(s, "approver_role", None) else None
                formatted_steps.append(
                    ApprovalStepResponse(
                        id=s.id,
                        workflow_id=s.workflow_id,
                        step_number=s.step_number,
                        approver_role_id=s.approver_role_id,
                        approver_role_name=role_name,
                        required_approvals=s.required_approvals,
                        auto_approve=s.auto_approve,
                        is_active=s.is_active,
                    )
                )

        return ApprovalWorkflowResponse(
            id=item.id,
            code=item.code,
            name=item.name,
            description=item.description,
            module_name=item.module_name,
            is_active=item.is_active,
            created_at=item.created_at,
            updated_at=item.updated_at,
            steps=formatted_steps,
        )
    except Exception as exc:
        print(f"EXC IN FORMAT WORKFLOW RESPONSE: {exc}")
        import traceback
        traceback.print_exc()
        raise exc


def _format_request_response(item: ApprovalRequest) -> ApprovalRequestResponse:
    """Helper formatting ApprovalRequest ORM entity to response schema."""
    wf_code = item.workflow.code if item.workflow else None
    wf_name = item.workflow.name if item.workflow else None
    sub_name = item.submitter.full_name if item.submitter else None

    formatted_history = []
    if item.history:
        for h in item.history:
            perf_name = h.performer.full_name if h.performer else None
            formatted_history.append(
                ApprovalHistoryResponse(
                    id=h.id,
                    approval_request_id=h.approval_request_id,
                    step_number=h.step_number,
                    action=h.action,
                    comments=h.comments,
                    performed_by=h.performed_by,
                    performer_name=perf_name,
                    action_time=h.action_time,
                )
            )

    return ApprovalRequestResponse(
        id=item.id,
        workflow_id=item.workflow_id,
        entity_type=item.entity_type,
        entity_id=item.entity_id,
        current_step_number=item.current_step_number,
        status=item.status,
        submitted_by=item.submitted_by,
        submitted_at=item.submitted_at,
        completed_at=item.completed_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
        workflow_code=wf_code,
        workflow_name=wf_name,
        submitter_name=sub_name,
        history=formatted_history,
    )


# --------------------------------------------------------------------------
# APPROVAL WORKFLOW DEFINITION ENDPOINTS
# --------------------------------------------------------------------------

@router.get(
    "/approval-workflows",
    response_model=ApprovalWorkflowListResponse,
    dependencies=[Depends(has_permission("workflow.read"))],
    summary="List Approval Workflows",
    description="Retrieves a paginated list of approval workflow definitions.",
)
async def list_approval_workflows(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    module_name: Optional[str] = Query(None, description="Filter by module name (e.g. leave, expense)"),
    db: AsyncSession = Depends(get_db),
):
    try:
        service = ApprovalWorkflowService(db)
        params = PaginationParams(page=page, page_size=page_size)

        filters = []
        if module_name:
            filters.append(FilterCriterion(field="module_name", value=module_name))

        paginated = await service.list_workflows(params=params, filters=filters)
        items = [_format_workflow_response(item) for item in paginated.items]

        return ApprovalWorkflowListResponse(
            items=items,
            total=paginated.total,
            page=paginated.page,
            page_size=paginated.page_size,
            total_pages=paginated.total_pages,
        )
    except Exception as exc:
        import logging, traceback
        logging.getLogger("app.api").error(f"Error in list_approval_workflows: {exc}\n{traceback.format_exc()}")
        raise exc


@router.post(
    "/approval-workflows",
    response_model=ApprovalWorkflowResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("workflow.create"))],
    summary="Create Approval Workflow",
    description="Creates a new reusable approval workflow definition and step sequence.",
)
async def create_approval_workflow(
    data: ApprovalWorkflowCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ApprovalWorkflowService(db)
    created = await service.create_workflow(data=data, current_user=current_user, request=request)
    return _format_workflow_response(created)


@router.put(
    "/approval-workflows/{id}",
    response_model=ApprovalWorkflowResponse,
    dependencies=[Depends(has_permission("workflow.update"))],
    summary="Update Approval Workflow",
    description="Updates an existing approval workflow definition and step sequence.",
)
async def update_approval_workflow(
    id: uuid.UUID,
    data: ApprovalWorkflowUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ApprovalWorkflowService(db)
    updated = await service.update_workflow(id=id, data=data, current_user=current_user, request=request)
    return _format_workflow_response(updated)


# --------------------------------------------------------------------------
# APPROVAL ENGINE EXECUTION ENDPOINTS
# --------------------------------------------------------------------------

@router.get(
    "/approval-requests",
    response_model=ApprovalRequestListResponse,
    dependencies=[Depends(has_permission("approval.read"))],
    summary="List Approval Requests",
    description="Retrieves a paginated list of approval request execution instances.",
)
async def list_approval_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (Draft, Pending, Approved, Rejected, Cancelled)"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    db: AsyncSession = Depends(get_db),
):
    engine = ApprovalEngineService(db)
    params = PaginationParams(page=page, page_size=page_size)

    filters = []
    if status_filter:
        filters.append(FilterCriterion(field="status", value=status_filter))
    if entity_type:
        filters.append(FilterCriterion(field="entity_type", value=entity_type))

    paginated = await engine.list_approval_requests(params=params, filters=filters)
    items = [_format_request_response(item) for item in paginated.items]

    return ApprovalRequestListResponse(
        items=items,
        total=paginated.total,
        page=paginated.page,
        page_size=paginated.page_size,
        total_pages=paginated.total_pages,
    )


@router.get(
    "/approval-requests/{id}",
    response_model=ApprovalRequestResponse,
    dependencies=[Depends(has_permission("approval.read"))],
    summary="Get Approval Request by ID",
    description="Retrieves details and immutable audit history for an approval request.",
)
async def get_approval_request(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    engine = ApprovalEngineService(db)
    item = await engine.get_approval_request_by_id(id)
    return _format_request_response(item)


@router.post(
    "/approval-requests",
    response_model=ApprovalRequestResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("approval.read"))],
    summary="Start Approval Workflow Request",
    description="Initiates an approval request for a target domain entity (entity_type, entity_id).",
)
async def start_approval_workflow(
    data: ApprovalRequestCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    engine = ApprovalEngineService(db)
    started = await engine.start_workflow(data=data, current_user=current_user, request=request)
    return _format_request_response(started)


@router.post(
    "/approval-requests/{id}/approve",
    response_model=ApprovalRequestResponse,
    dependencies=[Depends(has_permission("approval.approve"))],
    summary="Approve Current Step",
    description="Approves the current step of an active approval request. Advances step or completes workflow.",
)
async def approve_approval_step(
    id: uuid.UUID,
    data: ApprovalActionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    engine = ApprovalEngineService(db)
    approved = await engine.approve_step(id=id, data=data, current_user=current_user, request=request)
    return _format_request_response(approved)


@router.post(
    "/approval-requests/{id}/reject",
    response_model=ApprovalRequestResponse,
    dependencies=[Depends(has_permission("approval.reject"))],
    summary="Reject Approval Request",
    description="Rejects an active approval request at the current step (terminal state).",
)
async def reject_approval_step(
    id: uuid.UUID,
    data: ApprovalActionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    engine = ApprovalEngineService(db)
    rejected = await engine.reject_step(id=id, data=data, current_user=current_user, request=request)
    return _format_request_response(rejected)


@router.post(
    "/approval-requests/{id}/cancel",
    response_model=ApprovalRequestResponse,
    dependencies=[Depends(has_permission("approval.read"))],
    summary="Cancel Approval Request",
    description="Cancels an active approval request by submitter or administrator (terminal state).",
)
async def cancel_approval_workflow(
    id: uuid.UUID,
    data: ApprovalActionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    engine = ApprovalEngineService(db)
    cancelled = await engine.cancel_workflow(id=id, data=data, current_user=current_user, request=request)
    return _format_request_response(cancelled)
