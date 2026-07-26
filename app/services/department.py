import json
import logging
from typing import Any, Dict, List, Optional
import uuid
from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_manager
from app.exceptions.base import ApnaERPException
from app.models.department import Department
from app.models.user import User
from app.repositories.department import department_repository
from app.schemas.department import DepartmentCreate, DepartmentResponse, DepartmentTreeResponse, DepartmentUpdate
from app.tasks.department_tasks import send_department_notification_task
from app.utils.pagination import PaginationParams
from app.utils.audit import log_audit

logger = logging.getLogger("app.services.department")

CACHE_TREE_KEY = "department:tree"


class DepartmentService:
    """
    Business service layer managing Department entities, hierarchy tree, circular reference validation,
    active child deletion protection, Redis caching, audit logging, and background notifications.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = department_repository

    async def _invalidate_department_cache(self) -> None:
        """Clears Department tree cache from Redis."""
        try:
            await redis_manager.delete(CACHE_TREE_KEY)
            logger.info("[DepartmentService] Invalidated Redis tree cache.")
        except Exception as e:
            logger.warning(f"[DepartmentService] Redis cache invalidation error: {e}")

    async def _validate_no_circular_parent(self, department_id: uuid.UUID, new_parent_id: Optional[uuid.UUID]) -> None:
        """
        Validates that setting new_parent_id does not introduce a circular reference.
        """
        if not new_parent_id:
            return

        if department_id == new_parent_id:
            raise ApnaERPException(
                message="A department cannot be set as its own parent.",
                status_code=400,
                error_code="CIRCULAR_REFERENCE_ERROR"
            )

        curr_id: Optional[uuid.UUID] = new_parent_id
        visited = {department_id}

        while curr_id:
            if curr_id in visited:
                raise ApnaERPException(
                    message="Circular parent department reference detected in hierarchy chain.",
                    status_code=400,
                    error_code="CIRCULAR_REFERENCE_ERROR"
                )
            visited.add(curr_id)
            parent_dept = await self.repo.get_by_id(self.db, curr_id)
            if not parent_dept:
                break
            curr_id = parent_dept.parent_id

    async def create_department(
        self, data: DepartmentCreate, current_user: Optional[User] = None, request: Optional[Request] = None
    ) -> Department:
        """
        Creates a new department with unique code/name checks, parent validation, audit log, and cache invalidation.
        """
        # Validate unique code
        if await self.repo.exists_by_code(self.db, data.code):
            raise ApnaERPException(
                message=f"Department with code '{data.code}' already exists.",
                status_code=400,
                error_code="DUPLICATE_CODE_ERROR"
            )

        # Validate unique name
        if await self.repo.exists_by_name(self.db, data.name):
            raise ApnaERPException(
                message=f"Department with name '{data.name}' already exists.",
                status_code=400,
                error_code="DUPLICATE_NAME_ERROR"
            )

        # Validate parent department exists if specified
        if data.parent_id:
            parent = await self.repo.get_by_id(self.db, data.parent_id)
            if not parent:
                raise ApnaERPException(
                    message=f"Parent department with ID '{data.parent_id}' not found.",
                    status_code=404,
                    error_code="PARENT_NOT_FOUND"
                )

        department = await self.repo.create(self.db, obj_in=data)

        # Audit log
        await log_audit(
            db=self.db,
            action="DEPARTMENT_CREATE",
            entity_type="Department",
            entity_id=str(department.id),
            user_id=current_user.id if current_user else None,
            username=current_user.username if current_user else None,
            new_data={"code": department.code, "name": department.name, "parent_id": str(department.parent_id)},
            status_code=201,
        )

        # Invalidate Cache
        await self._invalidate_department_cache()

        # Trigger background Celery notification task
        try:
            send_department_notification_task.delay(
                event="DEPARTMENT_CREATE",
                department_id=str(department.id),
                code=department.code,
                name=department.name,
            )
        except Exception as e:
            logger.warning(f"[DepartmentService] Celery task enqueue failed: {e}")

        return department

    async def get_department_by_id(self, department_id: uuid.UUID) -> Department:
        """Retrieves a department by ID or raises 404."""
        dept = await self.repo.get_by_id(self.db, department_id)
        if not dept:
            raise ApnaERPException(
                message=f"Department with ID '{department_id}' not found.",
                status_code=404,
                error_code="DEPARTMENT_NOT_FOUND"
            )
        return dept

    async def get_departments_tree(self) -> List[DepartmentTreeResponse]:
        """
        Retrieves top-level root departments with nested children from Redis cache or database.
        Constructs hierarchy tree in memory cleanly to avoid lazy-loading issues.
        """
        # Try reading from Redis cache
        try:
            cached_raw = await redis_manager.get(CACHE_TREE_KEY)
            if cached_raw:
                logger.info("[DepartmentService] Returning department tree from Redis cache.")
                cached_data = json.loads(cached_raw)
                return [DepartmentTreeResponse.model_validate(item) for item in cached_data]
        except Exception as e:
            logger.warning(f"[DepartmentService] Redis cache read error: {e}")

        # Fetch all non-deleted departments from DB
        stmt = (
            select(Department)
            .where(Department.is_deleted == False)  # noqa: E712
            .order_by(Department.name)
        )
        res = await self.db.execute(stmt)
        all_depts = list(res.scalars().all())

        # Map to Pydantic tree nodes
        node_map: Dict[uuid.UUID, DepartmentTreeResponse] = {
            d.id: DepartmentTreeResponse(
                id=d.id,
                code=d.code,
                name=d.name,
                description=d.description,
                parent_id=d.parent_id,
                manager_id=d.manager_id,
                is_active=d.is_active,
                created_at=d.created_at,
                updated_at=d.updated_at,
                deleted_at=d.deleted_at,
                is_deleted=d.is_deleted,
                children=[],
            )
            for d in all_depts
        }

        root_nodes: List[DepartmentTreeResponse] = []
        for d in all_depts:
            node = node_map[d.id]
            if d.parent_id and d.parent_id in node_map:
                node_map[d.parent_id].children.append(node)
            else:
                root_nodes.append(node)

        # Save to Redis cache
        try:
            json_str = json.dumps([item.model_dump(mode="json") for item in root_nodes])
            await redis_manager.set(CACHE_TREE_KEY, json_str, ex=3600)
            logger.info("[DepartmentService] Cached department tree in Redis.")
        except Exception as e:
            logger.warning(f"[DepartmentService] Redis cache set error: {e}")

        return root_nodes

    async def get_departments_list(
        self, page: int = 1, page_size: int = 10, search: Optional[str] = None
    ) -> Dict[str, Any]:
        """Paginated list of departments."""
        params = PaginationParams(page=page, page_size=page_size)
        paginated_res = await self.repo.get_multi_paginated(
            self.db,
            params=params,
            search_term=search,
            search_fields=["name", "code"],
        )
        return {
            "total": paginated_res.total,
            "page": paginated_res.page,
            "page_size": paginated_res.page_size,
            "items": paginated_res.items,
        }

    async def update_department(
        self,
        department_id: uuid.UUID,
        data: DepartmentUpdate,
        current_user: Optional[User] = None,
        request: Optional[Request] = None
    ) -> Department:
        """
        Updates a department with unique validation, circular reference check, audit logging, and cache invalidation.
        """
        dept = await self.get_department_by_id(department_id)
        prev_data = {"code": dept.code, "name": dept.name, "parent_id": str(dept.parent_id)}

        update_dict = data.model_dump(exclude_unset=True)

        # Validate unique code if updating
        if "code" in update_dict and update_dict["code"] != dept.code:
            if await self.repo.exists_by_code(self.db, update_dict["code"], exclude_id=department_id):
                raise ApnaERPException(
                    message=f"Department code '{update_dict['code']}' is already in use.",
                    status_code=400,
                    error_code="DUPLICATE_CODE_ERROR"
                )

        # Validate unique name if updating
        if "name" in update_dict and update_dict["name"] != dept.name:
            if await self.repo.exists_by_name(self.db, update_dict["name"], exclude_id=department_id):
                raise ApnaERPException(
                    message=f"Department name '{update_dict['name']}' is already in use.",
                    status_code=400,
                    error_code="DUPLICATE_NAME_ERROR"
                )

        # Validate parent & circular reference if parent_id is being updated
        if "parent_id" in update_dict and update_dict["parent_id"] != dept.parent_id:
            new_parent_id = update_dict["parent_id"]
            if new_parent_id:
                parent = await self.repo.get_by_id(self.db, new_parent_id)
                if not parent:
                    raise ApnaERPException(
                        message=f"Parent department with ID '{new_parent_id}' not found.",
                        status_code=404,
                        error_code="PARENT_NOT_FOUND"
                    )
            await self._validate_no_circular_parent(department_id, new_parent_id)

        updated_dept = await self.repo.update(self.db, db_obj=dept, obj_in=data)

        # Audit Log
        await log_audit(
            db=self.db,
            action="DEPARTMENT_UPDATE",
            entity_type="Department",
            entity_id=str(department_id),
            user_id=current_user.id if current_user else None,
            username=current_user.username if current_user else None,
            previous_data=prev_data,
            new_data={"code": updated_dept.code, "name": updated_dept.name, "parent_id": str(updated_dept.parent_id)},
            status_code=200,
        )

        # Invalidate Cache
        await self._invalidate_department_cache()

        # Trigger background notification
        try:
            send_department_notification_task.delay(
                event="DEPARTMENT_UPDATE",
                department_id=str(updated_dept.id),
                code=updated_dept.code,
                name=updated_dept.name,
            )
        except Exception as e:
            logger.warning(f"[DepartmentService] Celery task enqueue failed: {e}")

        return updated_dept

    async def delete_department(
        self, department_id: uuid.UUID, current_user: Optional[User] = None, request: Optional[Request] = None
    ) -> Department:
        """
        Soft deletes a department after verifying no active child departments exist.
        """
        dept = await self.get_department_by_id(department_id)

        # Active children check
        children = await self.repo.get_children(self.db, department_id)
        if len(children) > 0:
            raise ApnaERPException(
                message=f"Cannot delete department '{dept.name}' because it has active child departments.",
                status_code=400,
                error_code="HAS_ACTIVE_CHILDREN_ERROR"
            )

        await self.repo.soft_delete(self.db, id=department_id)
        deleted_dept = await self.repo.get_by_id(self.db, department_id, include_deleted=True)

        # Audit Log
        await log_audit(
            db=self.db,
            action="DEPARTMENT_DELETE",
            entity_type="Department",
            entity_id=str(department_id),
            user_id=current_user.id if current_user else None,
            username=current_user.username if current_user else None,
            previous_data={"code": dept.code, "name": dept.name},
            new_data={"is_deleted": True},
            status_code=200,
        )

        # Invalidate Cache
        await self._invalidate_department_cache()

        # Trigger background notification
        try:
            send_department_notification_task.delay(
                event="DEPARTMENT_DELETE",
                department_id=str(dept.id),
                code=dept.code,
                name=dept.name,
            )
        except Exception as e:
            logger.warning(f"[DepartmentService] Celery task enqueue failed: {e}")

        return deleted_dept

    async def restore_department(
        self, department_id: uuid.UUID, current_user: Optional[User] = None, request: Optional[Request] = None
    ) -> Department:
        """Restores a soft-deleted department."""
        dept = await self.repo.get_by_id(self.db, department_id, include_deleted=True)
        if not dept:
            raise ApnaERPException(
                message=f"Department with ID '{department_id}' not found.",
                status_code=404,
                error_code="DEPARTMENT_NOT_FOUND"
            )

        if not dept.is_deleted:
            raise ApnaERPException(
                message="Department is not deleted.",
                status_code=400,
                error_code="NOT_DELETED_ERROR"
            )

        await self.repo.restore(self.db, id=department_id)
        restored_dept = await self.repo.get_by_id(self.db, department_id)

        # Audit Log
        await log_audit(
            db=self.db,
            action="DEPARTMENT_RESTORE",
            entity_type="Department",
            entity_id=str(department_id),
            user_id=current_user.id if current_user else None,
            username=current_user.username if current_user else None,
            previous_data={"is_deleted": True},
            new_data={"is_deleted": False},
            status_code=200,
        )

        # Invalidate Cache
        await self._invalidate_department_cache()

        return restored_dept
