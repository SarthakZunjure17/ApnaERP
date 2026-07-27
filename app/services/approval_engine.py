import datetime
import logging
from typing import Any, Dict, List, Optional
import uuid
from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_manager
from app.exceptions.base import ApnaERPException
from app.models.approval_workflow import (
    ApprovalHistory,
    ApprovalRequest,
    ApprovalStep,
    ApprovalWorkflow,
)
from app.models.user import User
from app.models.user_role import UserRole
from app.repositories.approval_workflow import (
    approval_history_repository,
    approval_request_repository,
    approval_step_repository,
    approval_workflow_repository,
)
from app.schemas.approval_workflow import (
    ApprovalActionRequest,
    ApprovalRequestCreate,
)
from app.tasks.approval_tasks import send_approval_notification_task
from app.utils.audit import log_audit
from app.utils.filters import FilterCriterion
from app.utils.pagination import PaginatedResult, PaginationParams

logger = logging.getLogger("app.services.approval_engine")

CACHE_REQ_PREFIX = "approval:request"


class ApprovalEngineService:
    """
    Service layer implementing the Enterprise Approval Workflow Engine.
    Executes role-based sequential step approvals, state transitions, immutable audit logs,
    Redis caching, and background notifications. Completely decoupled from domain business logic.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.workflow_repo = approval_workflow_repository
        self.step_repo = approval_step_repository
        self.request_repo = approval_request_repository
        self.history_repo = approval_history_repository

    async def _invalidate_cache(self, request_id: Optional[uuid.UUID] = None):
        """Invalidates Redis approval caches."""
        try:
            await redis_manager.delete_pattern("approval:*")
            if request_id:
                await redis_manager.delete(f"{CACHE_REQ_PREFIX}:{request_id}")
        except Exception as exc:
            logger.warning(f"Failed to clear Redis approval cache: {exc}")

    async def _user_has_role(self, user: User, role_id: uuid.UUID) -> bool:
        """Verifies if the specified user possesses the required approver role."""
        if user.is_superuser:
            return True

        query = select(UserRole).where(
            UserRole.user_id == user.id, UserRole.role_id == role_id
        )
        res = await self.db.execute(query)
        return res.scalars().first() is not None

    async def start_workflow(
        self,
        data: ApprovalRequestCreate,
        current_user: User,
        request: Optional[Request] = None,
    ) -> ApprovalRequest:
        """
        Starts a new approval request for a target domain entity (entity_type, entity_id).
        """
        # 1. Fetch Workflow definition
        workflow = await self.workflow_repo.get_by_code(self.db, data.workflow_code)
        if not workflow or not workflow.is_active or workflow.is_deleted:
            raise ApnaERPException(
                message=f"Approval workflow with code '{data.workflow_code}' not found or inactive.",
                status_code=404,
                error_code="WORKFLOW_NOT_FOUND",
            )

        if not workflow.steps:
            raise ApnaERPException(
                message=f"Workflow '{data.workflow_code}' has no active steps configured.",
                status_code=400,
                error_code="INVALID_WORKFLOW_DEFINITION",
            )

        # 2. Check for duplicate pending requests for the target entity
        existing = await self.request_repo.get_active_request_by_entity(
            self.db, entity_type=data.entity_type, entity_id=data.entity_id
        )
        if existing:
            raise ApnaERPException(
                message=f"An active pending approval request already exists for entity '{data.entity_type}:{data.entity_id}'.",
                status_code=400,
                error_code="DUPLICATE_APPROVAL_REQUEST",
            )

        now = datetime.datetime.now(datetime.timezone.utc)

        # 3. Create ApprovalRequest instance
        req_obj = ApprovalRequest(
            workflow_id=workflow.id,
            entity_type=data.entity_type,
            entity_id=str(data.entity_id),
            current_step_number=1,
            status="Pending",
            submitted_by=current_user.id,
            submitted_at=now,
        )
        self.db.add(req_obj)
        await self.db.flush()

        # 4. Create initial immutable ApprovalHistory entry
        history_entry = ApprovalHistory(
            approval_request_id=req_obj.id,
            step_number=1,
            action="Submitting",
            comments=data.comments,
            performed_by=current_user.id,
            action_time=now,
        )
        self.db.add(history_entry)

        await self.db.commit()
        await self.db.refresh(req_obj)
        await self._invalidate_cache(req_obj.id)

        # 5. Audit Log
        await log_audit(
            self.db,
            action="APPROVAL_WORKFLOW_START",
            entity_type="ApprovalRequest",
            entity_id=req_obj.id,
            user_id=current_user.id,
            username=current_user.username,
            previous_data=None,
            new_data={
                "workflow_code": workflow.code,
                "entity_type": req_obj.entity_type,
                "entity_id": req_obj.entity_id,
                "status": req_obj.status,
            },
            status_code=201,
        )

        # 6. Celery notification
        try:
            send_approval_notification_task.delay(
                event_type="WORKFLOW_STARTED",
                request_id=str(req_obj.id),
                workflow_code=workflow.code,
                entity_type=req_obj.entity_type,
                entity_id=req_obj.entity_id,
                current_step_number=1,
                status="Pending",
                performed_by_id=str(current_user.id),
                comments=data.comments,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery task for approval start: {exc}")

        return req_obj

    async def approve_step(
        self,
        id: uuid.UUID,
        data: ApprovalActionRequest,
        current_user: User,
        request: Optional[Request] = None,
    ) -> ApprovalRequest:
        """
        Approves the current step of an active ApprovalRequest.
        Advances to the next step or completes the workflow if no steps remain.
        """
        req_obj = await self.request_repo.get_by_id(self.db, id)
        if not req_obj or req_obj.is_deleted:
            raise ApnaERPException(
                message=f"Approval request with ID '{id}' not found.",
                status_code=404,
                error_code="APPROVAL_REQUEST_NOT_FOUND",
            )

        if req_obj.status != "Pending":
            raise ApnaERPException(
                message=f"Cannot approve request in '{req_obj.status}' status. Must be 'Pending'.",
                status_code=400,
                error_code="INVALID_WORKFLOW_TRANSITION",
            )

        # Fetch current step
        step = await self.step_repo.get_step_by_number(
            self.db, workflow_id=req_obj.workflow_id, step_number=req_obj.current_step_number
        )
        if not step:
            raise ApnaERPException(
                message=f"Approval step {req_obj.current_step_number} not found for workflow.",
                status_code=400,
                error_code="INVALID_WORKFLOW_STEP",
            )

        # Role Authorization Check
        has_role = await self._user_has_role(current_user, step.approver_role_id)
        if not has_role:
            raise ApnaERPException(
                message=f"User '{current_user.username}' is not authorized to approve step {step.step_number}.",
                status_code=403,
                error_code="UNAUTHORIZED_APPROVER",
            )

        now = datetime.datetime.now(datetime.timezone.utc)

        # Record immutable history
        history_entry = ApprovalHistory(
            approval_request_id=req_obj.id,
            step_number=req_obj.current_step_number,
            action="Approved Step",
            comments=data.comments,
            performed_by=current_user.id,
            action_time=now,
        )
        self.db.add(history_entry)

        # Check next step
        next_step = await self.step_repo.get_step_by_number(
            self.db, workflow_id=req_obj.workflow_id, step_number=req_obj.current_step_number + 1
        )

        prev_step_num = req_obj.current_step_number
        if next_step:
            # Advance step
            req_obj.current_step_number += 1
            event_type = "STEP_APPROVED"
        else:
            # Complete workflow
            req_obj.status = "Approved"
            req_obj.completed_at = now
            event_type = "WORKFLOW_APPROVED"

            # Final history log for completion
            completion_history = ApprovalHistory(
                approval_request_id=req_obj.id,
                step_number=prev_step_num,
                action="Completed Workflow",
                comments="All approval steps successfully completed",
                performed_by=current_user.id,
                action_time=now,
            )
            self.db.add(completion_history)

        await self.db.commit()
        await self.db.refresh(req_obj)
        await self._invalidate_cache(req_obj.id)

        # Audit Log
        await log_audit(
            self.db,
            action="APPROVAL_STEP_APPROVE",
            entity_type="ApprovalRequest",
            entity_id=req_obj.id,
            user_id=current_user.id,
            username=current_user.username,
            previous_data={"step_number": prev_step_num, "status": "Pending"},
            new_data={"step_number": req_obj.current_step_number, "status": req_obj.status},
            status_code=200,
        )

        try:
            send_approval_notification_task.delay(
                event_type=event_type,
                request_id=str(req_obj.id),
                workflow_code=req_obj.workflow.code if req_obj.workflow else "",
                entity_type=req_obj.entity_type,
                entity_id=req_obj.entity_id,
                current_step_number=req_obj.current_step_number,
                status=req_obj.status,
                performed_by_id=str(current_user.id),
                comments=data.comments,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery task for approval step: {exc}")

        return req_obj

    async def reject_step(
        self,
        id: uuid.UUID,
        data: ApprovalActionRequest,
        current_user: User,
        request: Optional[Request] = None,
    ) -> ApprovalRequest:
        """
        Rejects an active ApprovalRequest at the current step (Terminal state).
        """
        req_obj = await self.request_repo.get_by_id(self.db, id)
        if not req_obj or req_obj.is_deleted:
            raise ApnaERPException(
                message=f"Approval request with ID '{id}' not found.",
                status_code=404,
                error_code="APPROVAL_REQUEST_NOT_FOUND",
            )

        if req_obj.status != "Pending":
            raise ApnaERPException(
                message=f"Cannot reject request in '{req_obj.status}' status. Must be 'Pending'.",
                status_code=400,
                error_code="INVALID_WORKFLOW_TRANSITION",
            )

        step = await self.step_repo.get_step_by_number(
            self.db, workflow_id=req_obj.workflow_id, step_number=req_obj.current_step_number
        )
        if not step:
            raise ApnaERPException(
                message=f"Approval step {req_obj.current_step_number} not found.",
                status_code=400,
                error_code="INVALID_WORKFLOW_STEP",
            )

        has_role = await self._user_has_role(current_user, step.approver_role_id)
        if not has_role:
            raise ApnaERPException(
                message=f"User '{current_user.username}' is not authorized to reject step {step.step_number}.",
                status_code=403,
                error_code="UNAUTHORIZED_APPROVER",
            )

        now = datetime.datetime.now(datetime.timezone.utc)
        req_obj.status = "Rejected"
        req_obj.completed_at = now

        history_entry = ApprovalHistory(
            approval_request_id=req_obj.id,
            step_number=req_obj.current_step_number,
            action="Rejected",
            comments=data.comments,
            performed_by=current_user.id,
            action_time=now,
        )
        self.db.add(history_entry)

        await self.db.commit()
        await self.db.refresh(req_obj)
        await self._invalidate_cache(req_obj.id)

        await log_audit(
            self.db,
            action="APPROVAL_STEP_REJECT",
            entity_type="ApprovalRequest",
            entity_id=req_obj.id,
            user_id=current_user.id,
            username=current_user.username,
            previous_data={"status": "Pending"},
            new_data={"status": "Rejected", "comments": data.comments},
            status_code=200,
        )

        try:
            send_approval_notification_task.delay(
                event_type="WORKFLOW_REJECTED",
                request_id=str(req_obj.id),
                workflow_code=req_obj.workflow.code if req_obj.workflow else "",
                entity_type=req_obj.entity_type,
                entity_id=req_obj.entity_id,
                current_step_number=req_obj.current_step_number,
                status="Rejected",
                performed_by_id=str(current_user.id),
                comments=data.comments,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery task for approval rejection: {exc}")

        return req_obj

    async def cancel_workflow(
        self,
        id: uuid.UUID,
        data: ApprovalActionRequest,
        current_user: User,
        request: Optional[Request] = None,
    ) -> ApprovalRequest:
        """
        Cancels a pending ApprovalRequest by submitter or admin (Terminal state).
        """
        req_obj = await self.request_repo.get_by_id(self.db, id)
        if not req_obj or req_obj.is_deleted:
            raise ApnaERPException(
                message=f"Approval request with ID '{id}' not found.",
                status_code=404,
                error_code="APPROVAL_REQUEST_NOT_FOUND",
            )

        if req_obj.status != "Pending":
            raise ApnaERPException(
                message=f"Cannot cancel request in '{req_obj.status}' status. Must be 'Pending'.",
                status_code=400,
                error_code="INVALID_WORKFLOW_TRANSITION",
            )

        if req_obj.submitted_by != current_user.id and not current_user.is_superuser:
            raise ApnaERPException(
                message="Only the submitter or an administrator can cancel an active approval request.",
                status_code=403,
                error_code="UNAUTHORIZED_ACTION",
            )

        now = datetime.datetime.now(datetime.timezone.utc)
        req_obj.status = "Cancelled"
        req_obj.completed_at = now

        history_entry = ApprovalHistory(
            approval_request_id=req_obj.id,
            step_number=req_obj.current_step_number,
            action="Cancelled",
            comments=data.comments,
            performed_by=current_user.id,
            action_time=now,
        )
        self.db.add(history_entry)

        await self.db.commit()
        await self.db.refresh(req_obj)
        await self._invalidate_cache(req_obj.id)

        await log_audit(
            self.db,
            action="APPROVAL_WORKFLOW_CANCEL",
            entity_type="ApprovalRequest",
            entity_id=req_obj.id,
            user_id=current_user.id,
            username=current_user.username,
            previous_data={"status": "Pending"},
            new_data={"status": "Cancelled", "comments": data.comments},
            status_code=200,
        )

        try:
            send_approval_notification_task.delay(
                event_type="WORKFLOW_CANCELLED",
                request_id=str(req_obj.id),
                workflow_code=req_obj.workflow.code if req_obj.workflow else "",
                entity_type=req_obj.entity_type,
                entity_id=req_obj.entity_id,
                current_step_number=req_obj.current_step_number,
                status="Cancelled",
                performed_by_id=str(current_user.id),
                comments=data.comments,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery task for approval cancellation: {exc}")

        return req_obj

    async def get_approval_request_by_id(self, id: uuid.UUID) -> ApprovalRequest:
        """Retrieves a single ApprovalRequest by ID."""
        req_obj = await self.request_repo.get_by_id(self.db, id)
        if not req_obj or req_obj.is_deleted:
            raise ApnaERPException(
                message=f"Approval request with ID '{id}' not found.",
                status_code=404,
                error_code="APPROVAL_REQUEST_NOT_FOUND",
            )
        return req_obj

    async def list_approval_requests(
        self, params: PaginationParams, filters: Optional[List[FilterCriterion]] = None
    ) -> PaginatedResult[ApprovalRequest]:
        """Retrieves paginated list of all Approval Requests."""
        return await self.request_repo.get_multi_paginated(
            self.db, params=params, filters=filters
        )
