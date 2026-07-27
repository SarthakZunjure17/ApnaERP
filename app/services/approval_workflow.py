import logging
from typing import List, Optional
import uuid
from fastapi import Request
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_manager
from app.exceptions.base import ApnaERPException
from app.models.approval_workflow import ApprovalStep, ApprovalWorkflow
from app.models.role import Role
from app.models.user import User
from app.repositories.approval_workflow import (
    approval_step_repository,
    approval_workflow_repository,
)
from app.repositories.rbac import role_repository
from app.schemas.approval_workflow import (
    ApprovalWorkflowCreate,
    ApprovalWorkflowUpdate,
)
from app.utils.audit import log_audit
from app.utils.filters import FilterCriterion
from app.utils.pagination import PaginatedResult, PaginationParams

logger = logging.getLogger("app.services.approval_workflow")


class ApprovalWorkflowService:
    """
    Service layer for managing Approval Workflow definitions and step sequences.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = approval_workflow_repository
        self.step_repo = approval_step_repository
        self.role_repo = role_repository

    async def _invalidate_cache(self, workflow_id: Optional[uuid.UUID] = None):
        try:
            await redis_manager.delete_pattern("approval:workflow:*")
        except Exception as exc:
            logger.warning(f"Failed to clear Redis approval workflow cache: {exc}")

    async def create_workflow(
        self,
        data: ApprovalWorkflowCreate,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> ApprovalWorkflow:
        """Creates a new Approval Workflow definition along with its sequenced steps."""
        # 1. Code uniqueness check
        existing = await self.repository.get_by_code(self.db, data.code, include_deleted=True)
        if existing:
            raise ApnaERPException(
                message=f"Approval workflow with code '{data.code}' already exists.",
                status_code=400,
                error_code="DUPLICATE_WORKFLOW_CODE",
            )

        # 2. Validate roles in step definitions
        step_numbers = set()
        for step_in in data.steps:
            if step_in.step_number in step_numbers:
                raise ApnaERPException(
                    message=f"Duplicate step number {step_in.step_number} in workflow definition.",
                    status_code=400,
                    error_code="DUPLICATE_STEP_NUMBER",
                )
            step_numbers.add(step_in.step_number)

            role = await self.role_repo.get_by_id(self.db, step_in.approver_role_id)
            if not role or role.is_deleted:
                raise ApnaERPException(
                    message=f"Approver role with ID '{step_in.approver_role_id}' not found.",
                    status_code=404,
                    error_code="ROLE_NOT_FOUND",
                )

        wf_dict = data.model_dump(exclude={"steps"})
        workflow = await self.repository.create(self.db, obj_in=wf_dict)

        # Create step entities
        for step_in in data.steps:
            step_dict = step_in.model_dump()
            step_dict["workflow_id"] = workflow.id
            step_entity = ApprovalStep(**step_dict)
            self.db.add(step_entity)

        await self.db.commit()
        await self.db.refresh(workflow)
        await self._invalidate_cache(workflow.id)

        if current_user:
            await log_audit(
                self.db,
                action="WORKFLOW_CREATE",
                entity_type="ApprovalWorkflow",
                entity_id=workflow.id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data=None,
                new_data={"code": workflow.code, "name": workflow.name, "steps_count": len(data.steps)},
                status_code=201,
            )

        return workflow

    async def update_workflow(
        self,
        id: uuid.UUID,
        data: ApprovalWorkflowUpdate,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> ApprovalWorkflow:
        """Updates an existing Approval Workflow definition and step sequence."""
        workflow = await self.repository.get_by_id(self.db, id)
        if not workflow or workflow.is_deleted:
            raise ApnaERPException(
                message=f"Approval workflow with ID '{id}' not found.",
                status_code=404,
                error_code="WORKFLOW_NOT_FOUND",
            )

        prev_data = {"name": workflow.name, "is_active": workflow.is_active}

        if data.steps is not None:
            # Validate roles
            step_numbers = set()
            for step_in in data.steps:
                if step_in.step_number in step_numbers:
                    raise ApnaERPException(
                        message=f"Duplicate step number {step_in.step_number} in workflow update.",
                        status_code=400,
                        error_code="DUPLICATE_STEP_NUMBER",
                    )
                step_numbers.add(step_in.step_number)

                role = await self.role_repo.get_by_id(self.db, step_in.approver_role_id)
                if not role or role.is_deleted:
                    raise ApnaERPException(
                        message=f"Approver role with ID '{step_in.approver_role_id}' not found.",
                        status_code=404,
                        error_code="ROLE_NOT_FOUND",
                    )

            # Replace steps
            await self.db.execute(delete(ApprovalStep).where(ApprovalStep.workflow_id == id))
            for step_in in data.steps:
                step_dict = step_in.model_dump()
                step_dict["workflow_id"] = id
                step_entity = ApprovalStep(**step_dict)
                self.db.add(step_entity)

        update_dict = data.model_dump(exclude={"steps"}, exclude_unset=True)
        updated = await self.repository.update(self.db, db_obj=workflow, obj_in=update_dict)

        await self.db.commit()
        await self.db.refresh(updated)
        await self._invalidate_cache(updated.id)

        if current_user:
            await log_audit(
                self.db,
                action="WORKFLOW_UPDATE",
                entity_type="ApprovalWorkflow",
                entity_id=updated.id,
                user_id=current_user.id,
                username=current_user.username,
                previous_data=prev_data,
                new_data={"name": updated.name, "is_active": updated.is_active},
                status_code=200,
            )

        return updated

    async def get_workflow_by_id(self, id: uuid.UUID) -> ApprovalWorkflow:
        """Retrieves a single Approval Workflow definition by ID."""
        workflow = await self.repository.get_by_id(self.db, id)
        if not workflow or workflow.is_deleted:
            raise ApnaERPException(
                message=f"Approval workflow with ID '{id}' not found.",
                status_code=404,
                error_code="WORKFLOW_NOT_FOUND",
            )
        return workflow

    async def list_workflows(
        self, params: PaginationParams, filters: Optional[List[FilterCriterion]] = None
    ) -> PaginatedResult[ApprovalWorkflow]:
        """Retrieves paginated list of Approval Workflows."""
        return await self.repository.get_multi_paginated(
            self.db, params=params, filters=filters
        )
