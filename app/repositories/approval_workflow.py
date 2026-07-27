import logging
from typing import Any, List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval_workflow import (
    ApprovalHistory,
    ApprovalRequest,
    ApprovalStep,
    ApprovalWorkflow,
)
from app.repositories.base_repository import BaseRepository
from app.schemas.approval_workflow import (
    ApprovalStepCreate,
    ApprovalWorkflowCreate,
    ApprovalWorkflowUpdate,
)
from app.utils.filters import FilterCriterion
from app.utils.pagination import PaginatedResult, PaginationParams

logger = logging.getLogger("app.repositories.approval_workflow")


class ApprovalWorkflowRepository(
    BaseRepository[ApprovalWorkflow, ApprovalWorkflowCreate, ApprovalWorkflowUpdate]
):
    """
    Repository layer for ApprovalWorkflow entity definitions.
    """

    def __init__(self):
        super().__init__(ApprovalWorkflow)

    async def get_by_code(
        self, db: AsyncSession, code: str, include_deleted: bool = False
    ) -> Optional[ApprovalWorkflow]:
        """Retrieves an ApprovalWorkflow definition by its unique code."""
        query = select(ApprovalWorkflow).where(ApprovalWorkflow.code == code)
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)
        res = await db.execute(query)
        return res.unique().scalars().first()

    async def restore(self, db: AsyncSession, id: uuid.UUID) -> Optional[ApprovalWorkflow]:
        """Restores a soft-deleted ApprovalWorkflow definition."""
        obj = await self.get_by_id(db, id=id, include_deleted=True)
        if not obj or not obj.is_deleted:
            return obj

        obj.is_deleted = False
        obj.deleted_at = None
        await db.commit()
        await db.refresh(obj)
        logger.info(f"[ApprovalWorkflow] Restored soft-deleted workflow ID '{id}'")
        return obj


class ApprovalStepRepository(BaseRepository[ApprovalStep, ApprovalStepCreate, ApprovalStepCreate]):
    """
    Repository layer for ApprovalStep sequenced definitions.
    """

    def __init__(self):
        super().__init__(ApprovalStep)

    async def get_steps_by_workflow(
        self, db: AsyncSession, workflow_id: uuid.UUID
    ) -> List[ApprovalStep]:
        """Retrieves all active steps for a workflow ordered by step_number."""
        query = (
            select(ApprovalStep)
            .where(ApprovalStep.workflow_id == workflow_id, ApprovalStep.is_deleted.is_(False))
            .order_by(ApprovalStep.step_number)
        )
        res = await db.execute(query)
        return list(res.scalars().all())

    async def get_step_by_number(
        self, db: AsyncSession, workflow_id: uuid.UUID, step_number: int
    ) -> Optional[ApprovalStep]:
        """Retrieves a specific ApprovalStep by workflow ID and step_number."""
        query = select(ApprovalStep).where(
            ApprovalStep.workflow_id == workflow_id,
            ApprovalStep.step_number == step_number,
            ApprovalStep.is_deleted.is_(False),
        )
        res = await db.execute(query)
        return res.scalars().first()


class ApprovalRequestRepository(BaseRepository[ApprovalRequest, Any, Any]):
    """
    Repository layer for ApprovalRequest execution instances.
    """

    def __init__(self):
        super().__init__(ApprovalRequest)

    async def get_by_entity(
        self, db: AsyncSession, entity_type: str, entity_id: str, include_deleted: bool = False
    ) -> List[ApprovalRequest]:
        """Retrieves all approval requests for a target domain entity (entity_type, entity_id)."""
        query = select(ApprovalRequest).where(
            ApprovalRequest.entity_type == entity_type,
            ApprovalRequest.entity_id == str(entity_id),
        )
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)
        res = await db.execute(query)
        return list(res.scalars().all())

    async def get_active_request_by_entity(
        self, db: AsyncSession, entity_type: str, entity_id: str
    ) -> Optional[ApprovalRequest]:
        """Retrieves an active (Pending) approval request for a target domain entity."""
        query = select(ApprovalRequest).where(
            ApprovalRequest.entity_type == entity_type,
            ApprovalRequest.entity_id == str(entity_id),
            ApprovalRequest.status == "Pending",
            ApprovalRequest.is_deleted.is_(False),
        )
        res = await db.execute(query)
        return res.scalars().first()

    async def restore(self, db: AsyncSession, id: uuid.UUID) -> Optional[ApprovalRequest]:
        """Restores a soft-deleted ApprovalRequest."""
        obj = await self.get_by_id(db, id=id, include_deleted=True)
        if not obj or not obj.is_deleted:
            return obj

        obj.is_deleted = False
        obj.deleted_at = None
        await db.commit()
        await db.refresh(obj)
        logger.info(f"[ApprovalRequest] Restored soft-deleted request ID '{id}'")
        return obj


class ApprovalHistoryRepository(BaseRepository[ApprovalHistory, Any, Any]):
    """
    Repository layer for immutable ApprovalHistory audit entries.
    """

    def __init__(self):
        super().__init__(ApprovalHistory)

    async def get_history_by_request(
        self, db: AsyncSession, approval_request_id: uuid.UUID
    ) -> List[ApprovalHistory]:
        """Retrieves immutable history logs for a request ordered by action_time."""
        query = (
            select(ApprovalHistory)
            .where(ApprovalHistory.approval_request_id == approval_request_id)
            .order_by(ApprovalHistory.action_time)
        )
        res = await db.execute(query)
        return list(res.scalars().all())


approval_workflow_repository = ApprovalWorkflowRepository()
approval_step_repository = ApprovalStepRepository()
approval_request_repository = ApprovalRequestRepository()
approval_history_repository = ApprovalHistoryRepository()
