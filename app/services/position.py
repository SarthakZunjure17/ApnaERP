import logging
from typing import Any, Dict, List, Optional
import uuid
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.base import ApnaERPException
from app.core.redis import redis_manager
from app.models.position import Position
from app.models.user import User
from app.repositories.department import department_repository
from app.repositories.position import position_repository
from app.schemas.position import (
    PositionCreate,
    PositionResponse,
    PositionTreeResponse,
    PositionUpdate,
)
from app.services.base_service import BaseService
from app.tasks.position_tasks import send_position_notification_task
from app.utils.audit import log_audit
from app.utils.pagination import PaginatedResult, PaginationParams

logger = logging.getLogger("app.services.position")

POSITION_TREE_CACHE_KEY = "position:tree"
POSITION_LIST_CACHE_PREFIX = "position:list:"


class PositionService(BaseService[position_repository.__class__]):
    """
    Business service layer for Position Management.
    Enforces uniqueness, hierarchy loop prevention, headcount constraints,
    Redis caching, audit trails, and Celery event telemetry.
    """
    def __init__(self, db: AsyncSession):
        super().__init__(position_repository)
        self.db = db
        self.dept_repo = department_repository

    async def _invalidate_caches(self, department_id: Optional[uuid.UUID] = None) -> None:
        """Invalidates Redis cache keys for position tree and lists."""
        try:
            await redis_manager.delete(POSITION_TREE_CACHE_KEY)
            if department_id:
                await redis_manager.delete(f"{POSITION_LIST_CACHE_PREFIX}{department_id}")
            await redis_manager.delete_pattern(f"{POSITION_LIST_CACHE_PREFIX}*")
            await redis_manager.delete_pattern(f"{POSITION_TREE_CACHE_KEY}*")
        except Exception as exc:
            logger.warning(f"Failed to invalidate position Redis caches: {exc}")

    async def _validate_no_circular_position(
        self, position_id: uuid.UUID, new_parent_id: uuid.UUID
    ) -> None:
        """Prevents circular position reporting loops (e.g. A -> B -> C -> A)."""
        if position_id == new_parent_id:
            raise ApnaERPException(
                message="Position cannot be its own parent position.",
                status_code=400,
                error_code="CIRCULAR_POSITION_HIERARCHY",
            )

        curr_id: Optional[uuid.UUID] = new_parent_id
        visited = {position_id}

        while curr_id is not None:
            if curr_id in visited:
                raise ApnaERPException(
                    message="Circular position reporting hierarchy loop detected.",
                    status_code=400,
                    error_code="CIRCULAR_POSITION_HIERARCHY",
                )
            visited.add(curr_id)
            parent_obj = await self.repository.get_by_id(self.db, curr_id)
            curr_id = parent_obj.parent_position_id if parent_obj else None

    async def create_position(
        self,
        data: PositionCreate,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> Position:
        """Creates a new enterprise Position record with business rule validations."""
        # 1. Validate owning Department existence & active status
        dept = await self.dept_repo.get_by_id(self.db, data.department_id)
        if not dept or getattr(dept, "is_deleted", False):
            raise ApnaERPException(
                message=f"Department with ID '{data.department_id}' not found.",
                status_code=404,
                error_code="DEPARTMENT_NOT_FOUND",
            )
        if not dept.is_active:
            raise ApnaERPException(
                message=f"Cannot assign position to inactive department '{dept.name}'.",
                status_code=400,
                error_code="INACTIVE_DEPARTMENT",
            )

        # 2. Check unique Position Code
        if await self.repository.exists_by_code(self.db, data.code):
            raise ApnaERPException(
                message=f"Position code '{data.code}' already exists.",
                status_code=400,
                error_code="DUPLICATE_POSITION_CODE",
            )

        # 3. Check Position Title unique within Department
        existing_title = await self.repository.get_by_department_and_title(
            self.db, data.department_id, data.title
        )
        if existing_title:
            raise ApnaERPException(
                message=f"Position title '{data.title}' already exists in department '{dept.name}'.",
                status_code=400,
                error_code="DUPLICATE_POSITION_TITLE",
            )

        # 4. Validate Parent Position if provided
        if data.parent_position_id:
            parent_pos = await self.repository.get_by_id(self.db, data.parent_position_id)
            if not parent_pos or getattr(parent_pos, "is_deleted", False):
                raise ApnaERPException(
                    message=f"Parent position with ID '{data.parent_position_id}' not found.",
                    status_code=404,
                    error_code="PARENT_POSITION_NOT_FOUND",
                )
            if not parent_pos.is_active:
                raise ApnaERPException(
                    message=f"Cannot assign inactive parent position '{parent_pos.title}'.",
                    status_code=400,
                    error_code="INACTIVE_PARENT_POSITION",
                )

        # 5. Create Record
        position = await self.repository.create(self.db, obj_in=data)

        # 6. Cache Invalidation, Audit Log & Celery Telemetry
        await self._invalidate_caches(data.department_id)
        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else None

        await log_audit(
            self.db,
            action="POSITION_CREATE",
            entity_type="Position",
            entity_id=position.id,
            user_id=user_id,
            username=username,
            new_data={"code": position.code, "title": position.title, "department_id": str(position.department_id)},
            status_code=201,
        )

        try:
            send_position_notification_task.delay(
                event_type="POSITION_CREATE",
                position_id=str(position.id),
                position_code=position.code,
                position_title=position.title,
                user_id=str(user_id) if user_id else None,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery position notification task: {exc}")

        return position

    async def get_position_by_id(self, position_id: uuid.UUID) -> Position:
        """Retrieves a single Position by UUID."""
        pos = await self.repository.get_by_id(self.db, position_id)
        if not pos or getattr(pos, "is_deleted", False):
            raise ApnaERPException(
                message=f"Position with ID '{position_id}' not found.",
                status_code=404,
                error_code="POSITION_NOT_FOUND",
            )
        return pos

    async def get_positions_list(
        self,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        department_id: Optional[uuid.UUID] = None,
        is_active: Optional[bool] = None,
    ) -> PaginatedResult[Position]:
        """Retrieves paginated position records with filtering and search."""
        params = PaginationParams(page=page, page_size=page_size)
        filters = []
        if department_id:
            from app.utils.filters import FilterCriterion, FilterOperator
            filters.append(FilterCriterion(field="department_id", operator=FilterOperator.EQ, value=department_id))
        if is_active is not None:
            from app.utils.filters import FilterCriterion, FilterOperator
            filters.append(FilterCriterion(field="is_active", operator=FilterOperator.EQ, value=is_active))

        return await self.repository.get_multi_paginated(
            self.db,
            params=params,
            filters=filters,
            search_term=search,
            search_fields=["code", "title", "grade", "level"],
        )

    async def get_positions_by_department(self, department_id: uuid.UUID) -> List[Position]:
        """Retrieves all positions belonging to a department."""
        dept = await self.dept_repo.get_by_id(self.db, department_id)
        if not dept or getattr(dept, "is_deleted", False):
            raise ApnaERPException(
                message=f"Department with ID '{department_id}' not found.",
                status_code=404,
                error_code="DEPARTMENT_NOT_FOUND",
            )
        return await self.repository.get_by_department(self.db, department_id)

    async def _build_tree_node(self, pos: Position) -> PositionTreeResponse:
        """Recursively builds hierarchy tree nodes."""
        children_objs = await self.repository.get_children(self.db, pos.id)
        child_nodes = []
        for child in children_objs:
            if child.is_active and not child.is_deleted:
                child_nodes.append(await self._build_tree_node(child))

        dept_name = pos.department.name if pos.department else None

        return PositionTreeResponse(
            id=pos.id,
            code=pos.code,
            title=pos.title,
            department_id=pos.department_id,
            department_name=dept_name,
            employment_category=pos.employment_category,
            maximum_headcount=pos.maximum_headcount,
            current_headcount=pos.current_headcount,
            is_managerial=pos.is_managerial,
            is_active=pos.is_active,
            children=child_nodes,
        )

    async def get_position_tree(
        self, department_id: Optional[uuid.UUID] = None
    ) -> List[PositionTreeResponse]:
        """Retrieves position hierarchy tree with Redis caching."""
        cache_key = f"{POSITION_TREE_CACHE_KEY}:{department_id}" if department_id else POSITION_TREE_CACHE_KEY
        try:
            cached_data = await redis_manager.get_json(cache_key)
            if cached_data:
                return [PositionTreeResponse.model_validate(item) for item in cached_data]
        except Exception as exc:
            logger.warning(f"Failed to fetch position tree from Redis cache: {exc}")

        roots = await self.repository.get_tree(self.db, department_id=department_id)
        tree = []
        for root in roots:
            if root.is_active and not root.is_deleted:
                tree.append(await self._build_tree_node(root))

        try:
            serialized_tree = [node.model_dump(mode="json") for node in tree]
            await redis_manager.set_json(cache_key, serialized_tree, ttl=3600)
        except Exception as exc:
            logger.warning(f"Failed to store position tree in Redis cache: {exc}")

        return tree

    async def update_position(
        self,
        position_id: uuid.UUID,
        data: PositionUpdate,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> Position:
        """Updates position metadata, department, parent position, or headcount limits."""
        pos = await self.get_position_by_id(position_id)

        # 1. Code uniqueness check
        if data.code is not None and data.code.lower() != pos.code.lower():
            if await self.repository.exists_by_code(self.db, data.code):
                raise ApnaERPException(
                    message=f"Position code '{data.code}' already exists.",
                    status_code=400,
                    error_code="DUPLICATE_POSITION_CODE",
                )

        # 2. Title & Department uniqueness check
        target_dept_id = data.department_id if data.department_id is not None else pos.department_id
        target_title = data.title if data.title is not None else pos.title

        if data.title is not None or data.department_id is not None:
            dept = await self.dept_repo.get_by_id(self.db, target_dept_id)
            if not dept or getattr(dept, "is_deleted", False):
                raise ApnaERPException(
                    message=f"Department with ID '{target_dept_id}' not found.",
                    status_code=404,
                    error_code="DEPARTMENT_NOT_FOUND",
                )
            if not dept.is_active:
                raise ApnaERPException(
                    message=f"Cannot assign position to inactive department '{dept.name}'.",
                    status_code=400,
                    error_code="INACTIVE_DEPARTMENT",
                )

            existing = await self.repository.get_by_department_and_title(
                self.db, target_dept_id, target_title
            )
            if existing and existing.id != pos.id:
                raise ApnaERPException(
                    message=f"Position title '{target_title}' already exists in department '{dept.name}'.",
                    status_code=400,
                    error_code="DUPLICATE_POSITION_TITLE",
                )

        # 3. Parent Position & Circular hierarchy check
        if data.parent_position_id is not None and data.parent_position_id != pos.parent_position_id:
            parent_pos = await self.repository.get_by_id(self.db, data.parent_position_id)
            if not parent_pos or getattr(parent_pos, "is_deleted", False):
                raise ApnaERPException(
                    message=f"Parent position with ID '{data.parent_position_id}' not found.",
                    status_code=404,
                    error_code="PARENT_POSITION_NOT_FOUND",
                )
            if not parent_pos.is_active:
                raise ApnaERPException(
                    message=f"Cannot assign inactive parent position '{parent_pos.title}'.",
                    status_code=400,
                    error_code="INACTIVE_PARENT_POSITION",
                )
            await self._validate_no_circular_position(pos.id, data.parent_position_id)

        # 4. Maximum headcount constraint validation
        if data.maximum_headcount is not None:
            if data.maximum_headcount < pos.current_headcount:
                raise ApnaERPException(
                    message=f"Maximum headcount ({data.maximum_headcount}) cannot be less than current assigned headcount ({pos.current_headcount}).",
                    status_code=400,
                    error_code="HEADCOUNT_CAPACITY_EXCEEDED",
                )

        updated_pos = await self.repository.update(self.db, db_obj=pos, obj_in=data)
        await self._invalidate_caches(target_dept_id)

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else None

        await log_audit(
            self.db,
            action="POSITION_UPDATE",
            entity_type="Position",
            entity_id=updated_pos.id,
            user_id=user_id,
            username=username,
            new_data=data.model_dump(exclude_unset=True),
            status_code=200,
        )

        try:
            send_position_notification_task.delay(
                event_type="POSITION_UPDATE",
                position_id=str(updated_pos.id),
                position_code=updated_pos.code,
                position_title=updated_pos.title,
                user_id=str(user_id) if user_id else None,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery position update notification task: {exc}")

        fresh_pos = await self.repository.get_by_id(self.db, updated_pos.id)
        return fresh_pos if fresh_pos else updated_pos

    async def delete_position(
        self,
        position_id: uuid.UUID,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> Position:
        """Soft-deletes a Position record with assignment guards."""
        pos = await self.get_position_by_id(position_id)

        if pos.current_headcount > 0:
            raise ApnaERPException(
                message=f"Cannot delete position '{pos.title}' with active assigned employees (Headcount: {pos.current_headcount}).",
                status_code=400,
                error_code="ASSIGNED_EMPLOYEES_EXIST",
            )

        children = await self.repository.get_children(self.db, pos.id)
        if len(children) > 0:
            raise ApnaERPException(
                message=f"Cannot delete position '{pos.title}' because it has {len(children)} child reporting positions.",
                status_code=400,
                error_code="HAS_CHILD_POSITIONS",
            )

        await self.repository.soft_delete(self.db, id=pos.id)
        await self._invalidate_caches(pos.department_id)

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else None

        await log_audit(
            self.db,
            action="POSITION_DELETE",
            entity_type="Position",
            entity_id=pos.id,
            user_id=user_id,
            username=username,
            status_code=200,
        )

        try:
            send_position_notification_task.delay(
                event_type="POSITION_DELETE",
                position_id=str(pos.id),
                position_code=pos.code,
                position_title=pos.title,
                user_id=str(user_id) if user_id else None,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery position deletion notification task: {exc}")

        deleted_pos = await self.repository.get_by_id(self.db, pos.id, include_deleted=True)
        return deleted_pos if deleted_pos else pos

    async def restore_position(
        self,
        position_id: uuid.UUID,
        current_user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> Position:
        """Restores a soft-deleted Position."""
        pos = await self.repository.get_by_id(self.db, position_id, include_deleted=True)
        if not pos or not getattr(pos, "is_deleted", False):
            raise ApnaERPException(
                message=f"Soft-deleted position with ID '{position_id}' not found.",
                status_code=404,
                error_code="POSITION_NOT_FOUND",
            )

        await self.repository.restore(self.db, id=pos.id)
        await self._invalidate_caches(pos.department_id)

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else None

        await log_audit(
            self.db,
            action="POSITION_RESTORE",
            entity_type="Position",
            entity_id=pos.id,
            user_id=user_id,
            username=username,
            status_code=200,
        )

        restored_pos = await self.repository.get_by_id(self.db, pos.id)
        return restored_pos if restored_pos else pos

