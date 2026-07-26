import json
import logging
from typing import Any, Dict, List, Optional
import uuid
from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_manager
from app.exceptions.base import ApnaERPException
from app.models.employee import Employee
from app.models.user import User
from app.repositories.department import department_repository
from app.repositories.employee import employee_repository
from app.repositories.file import file_repository
from app.repositories.user import user_repository
from app.schemas.employee import EmployeeCreate, EmployeeHierarchyResponse, EmployeeResponse, EmployeeUpdate
from app.tasks.employee_tasks import send_employee_notification_task
from app.utils.audit import log_audit
from app.utils.pagination import PaginationParams

logger = logging.getLogger("app.services.employee")

CACHE_HIERARCHY_KEY = "employee:hierarchy"
CACHE_DEPT_PREFIX = "employee:department:"


class EmployeeService:
    """
    Business service layer managing Employee entities, reporting hierarchy validation, department constraints,
    Redis caching, audit logging, and background event notifications.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = employee_repository
        self.dept_repo = department_repository
        self.user_repo = user_repository
        self.file_repo = file_repository

    async def _invalidate_employee_caches(self, department_id: Optional[uuid.UUID] = None) -> None:
        """Clears employee hierarchy and department caches from Redis."""
        try:
            keys_to_delete = [CACHE_HIERARCHY_KEY]
            if department_id:
                keys_to_delete.append(f"{CACHE_DEPT_PREFIX}{department_id}")
            await redis_manager.delete(*keys_to_delete)
            logger.info("[EmployeeService] Invalidated Redis employee caches.")
        except Exception as e:
            logger.warning(f"[EmployeeService] Redis cache invalidation error: {e}")

    async def _validate_no_circular_manager(self, employee_id: uuid.UUID, new_manager_id: Optional[uuid.UUID]) -> None:
        """
        Validates that setting new_manager_id does not create a circular reporting hierarchy loop.
        """
        if not new_manager_id:
            return

        if employee_id == new_manager_id:
            raise ApnaERPException(
                message="An employee cannot manage themselves.",
                status_code=400,
                error_code="SELF_MANAGEMENT_ERROR"
            )

        curr_id: Optional[uuid.UUID] = new_manager_id
        visited = {employee_id}

        while curr_id:
            if curr_id in visited:
                raise ApnaERPException(
                    message="Circular manager reporting hierarchy detected.",
                    status_code=400,
                    error_code="CIRCULAR_REPORTING_ERROR"
                )
            visited.add(curr_id)
            manager_emp = await self.repo.get_by_id(self.db, curr_id)
            if not manager_emp:
                break
            curr_id = manager_emp.manager_id

    async def _validate_department(self, department_id: uuid.UUID) -> None:
        """Validates that department exists, is active, and is not deleted."""
        dept = await self.dept_repo.get_by_id(self.db, department_id)
        if not dept or dept.is_deleted:
            raise ApnaERPException(
                message=f"Department with ID '{department_id}' not found.",
                status_code=404,
                error_code="DEPARTMENT_NOT_FOUND"
            )

        if not dept.is_active:
            raise ApnaERPException(
                message=f"Department '{dept.name}' is inactive and cannot receive employees.",
                status_code=400,
                error_code="INACTIVE_DEPARTMENT_ERROR"
            )

    async def create_employee(
        self, data: EmployeeCreate, current_user: Optional[User] = None, request: Optional[Request] = None
    ) -> Employee:
        """
        Creates a new employee after validating unique fields, department status, dates, manager hierarchy, user link, and profile photo.
        """
        # Validate unique employee code
        if await self.repo.exists_by_code(self.db, data.employee_code):
            raise ApnaERPException(
                message=f"Employee code '{data.employee_code}' already exists.",
                status_code=400,
                error_code="DUPLICATE_CODE_ERROR"
            )

        # Validate unique work email
        if await self.repo.exists_by_work_email(self.db, data.work_email):
            raise ApnaERPException(
                message=f"Work email '{data.work_email}' already exists.",
                status_code=400,
                error_code="DUPLICATE_EMAIL_ERROR"
            )

        # Validate dates
        if data.exit_date and data.joining_date > data.exit_date:
            raise ApnaERPException(
                message="Joining date cannot be after exit date.",
                status_code=400,
                error_code="INVALID_DATES_ERROR"
            )

        # Validate department
        await self._validate_department(data.department_id)

        # Validate manager existence if provided
        if data.manager_id:
            manager = await self.repo.get_by_id(self.db, data.manager_id)
            if not manager or manager.is_deleted:
                raise ApnaERPException(
                    message=f"Manager with ID '{data.manager_id}' not found.",
                    status_code=404,
                    error_code="MANAGER_NOT_FOUND"
                )

        # Validate linked User ID if provided
        if data.user_id:
            linked_user = await self.user_repo.get_by_id(self.db, data.user_id)
            if not linked_user:
                raise ApnaERPException(
                    message=f"User with ID '{data.user_id}' not found.",
                    status_code=404,
                    error_code="USER_NOT_FOUND"
                )
            if await self.repo.exists_by_user_id(self.db, data.user_id):
                raise ApnaERPException(
                    message=f"User ID '{data.user_id}' is already linked to another employee.",
                    status_code=400,
                    error_code="USER_ALREADY_LINKED"
                )

        # Validate profile photo file if provided
        if data.profile_photo_file_id:
            profile_file = await self.file_repo.get_by_id(self.db, data.profile_photo_file_id)
            if not profile_file:
                raise ApnaERPException(
                    message=f"File with ID '{data.profile_photo_file_id}' not found.",
                    status_code=404,
                    error_code="FILE_NOT_FOUND"
                )

        employee = await self.repo.create(self.db, obj_in=data)

        # Audit log
        await log_audit(
            db=self.db,
            action="EMPLOYEE_CREATE",
            entity_type="Employee",
            entity_id=str(employee.id),
            user_id=current_user.id if current_user else None,
            username=current_user.username if current_user else None,
            new_data={
                "code": employee.employee_code,
                "email": employee.work_email,
                "department_id": str(employee.department_id),
            },
            status_code=201,
        )

        # Invalidate Cache
        await self._invalidate_employee_caches(department_id=employee.department_id)

        # Dispatch background notification
        try:
            send_employee_notification_task.delay(
                event="EMPLOYEE_CREATE",
                employee_id=str(employee.id),
                code=employee.employee_code,
                email=employee.work_email,
            )
        except Exception as e:
            logger.warning(f"[EmployeeService] Celery task enqueue failed: {e}")

        return employee

    async def get_employee_by_id(self, employee_id: uuid.UUID) -> Employee:
        """Retrieves an active employee by ID."""
        emp = await self.repo.get_by_id(self.db, employee_id)
        if not emp or emp.is_deleted:
            raise ApnaERPException(
                message=f"Employee with ID '{employee_id}' not found.",
                status_code=404,
                error_code="EMPLOYEE_NOT_FOUND"
            )
        return emp

    async def get_employees_by_department(self, department_id: uuid.UUID) -> List[Employee]:
        """Retrieves active employees in a department, cached via Redis."""
        cache_key = f"{CACHE_DEPT_PREFIX}{department_id}"
        try:
            cached_raw = await redis_manager.get(cache_key)
            if cached_raw:
                logger.info(f"[EmployeeService] Returning employees for dept '{department_id}' from Redis.")
                items = json.loads(cached_raw)
                # Re-fetch from DB if format check
                return await self.repo.get_by_department(self.db, department_id)
        except Exception as e:
            logger.warning(f"[EmployeeService] Redis cache read error: {e}")

        employees = await self.repo.get_by_department(self.db, department_id)

        try:
            json_str = json.dumps([str(e.id) for e in employees])
            await redis_manager.set(cache_key, json_str, ex=3600)
        except Exception as e:
            logger.warning(f"[EmployeeService] Redis cache write error: {e}")

        return employees

    async def get_employee_hierarchy(self) -> List[EmployeeHierarchyResponse]:
        """
        Retrieves top-level root managers (manager_id IS NULL) with nested direct reports hierarchy from cache or DB.
        """
        try:
            cached_raw = await redis_manager.get(CACHE_HIERARCHY_KEY)
            if cached_raw:
                logger.info("[EmployeeService] Returning employee hierarchy from Redis cache.")
                cached_data = json.loads(cached_raw)
                return [EmployeeHierarchyResponse.model_validate(item) for item in cached_data]
        except Exception as e:
            logger.warning(f"[EmployeeService] Redis hierarchy cache read error: {e}")

        stmt = (
            select(Employee)
            .where(Employee.is_deleted == False)  # noqa: E712
            .order_by(Employee.first_name, Employee.last_name)
        )
        res = await self.db.execute(stmt)
        all_emps = list(res.scalars().all())

        node_map: Dict[uuid.UUID, EmployeeHierarchyResponse] = {
            e.id: EmployeeHierarchyResponse(
                id=e.id,
                employee_code=e.employee_code,
                first_name=e.first_name,
                middle_name=e.middle_name,
                last_name=e.last_name,
                preferred_name=e.preferred_name,
                work_email=e.work_email,
                personal_email=e.personal_email,
                work_phone=e.work_phone,
                personal_phone=e.personal_phone,
                user_id=e.user_id,
                department_id=e.department_id,
                manager_id=e.manager_id,
                employment_type=e.employment_type,
                employment_status=e.employment_status,
                joining_date=e.joining_date,
                confirmation_date=e.confirmation_date,
                exit_date=e.exit_date,
                date_of_birth=e.date_of_birth,
                gender=e.gender,
                profile_photo_file_id=e.profile_photo_file_id,
                is_active=e.is_active,
                created_at=e.created_at,
                updated_at=e.updated_at,
                deleted_at=e.deleted_at,
                is_deleted=e.is_deleted,
                direct_reports=[],
            )
            for e in all_emps
        }

        root_nodes: List[EmployeeHierarchyResponse] = []
        for e in all_emps:
            node = node_map[e.id]
            if e.manager_id and e.manager_id in node_map:
                node_map[e.manager_id].direct_reports.append(node)
            else:
                root_nodes.append(node)

        try:
            json_str = json.dumps([item.model_dump(mode="json") for item in root_nodes])
            await redis_manager.set(CACHE_HIERARCHY_KEY, json_str, ex=3600)
            logger.info("[EmployeeService] Cached employee hierarchy in Redis.")
        except Exception as e:
            logger.warning(f"[EmployeeService] Redis hierarchy cache set error: {e}")

        return root_nodes

    async def get_employees_list(
        self, page: int = 1, page_size: int = 10, search: Optional[str] = None
    ) -> Dict[str, Any]:
        """Paginated list of employees with search."""
        params = PaginationParams(page=page, page_size=page_size)
        paginated_res = await self.repo.get_multi_paginated(
            self.db,
            params=params,
            search_term=search,
            search_fields=["first_name", "last_name", "employee_code", "work_email"],
        )
        return {
            "total": paginated_res.total,
            "page": paginated_res.page,
            "page_size": paginated_res.page_size,
            "items": paginated_res.items,
        }

    async def update_employee(
        self,
        employee_id: uuid.UUID,
        data: EmployeeUpdate,
        current_user: Optional[User] = None,
        request: Optional[Request] = None
    ) -> Employee:
        """Updates employee after executing validations."""
        emp = await self.get_employee_by_id(employee_id)
        prev_data = {
            "code": emp.employee_code,
            "email": emp.work_email,
            "department_id": str(emp.department_id),
            "manager_id": str(emp.manager_id) if emp.manager_id else None,
        }

        update_dict = data.model_dump(exclude_unset=True)

        # Unique code
        if "employee_code" in update_dict and update_dict["employee_code"] != emp.employee_code:
            if await self.repo.exists_by_code(self.db, update_dict["employee_code"], exclude_id=employee_id):
                raise ApnaERPException(
                    message=f"Employee code '{update_dict['employee_code']}' is already in use.",
                    status_code=400,
                    error_code="DUPLICATE_CODE_ERROR"
                )

        # Unique email
        if "work_email" in update_dict and update_dict["work_email"] != emp.work_email:
            if await self.repo.exists_by_work_email(self.db, update_dict["work_email"], exclude_id=employee_id):
                raise ApnaERPException(
                    message=f"Work email '{update_dict['work_email']}' is already in use.",
                    status_code=400,
                    error_code="DUPLICATE_EMAIL_ERROR"
                )

        # Dates check
        joining_date = update_dict.get("joining_date", emp.joining_date)
        exit_date = update_dict.get("exit_date", emp.exit_date)
        if exit_date and joining_date > exit_date:
            raise ApnaERPException(
                message="Joining date cannot be after exit date.",
                status_code=400,
                error_code="INVALID_DATES_ERROR"
            )

        # Department check
        if "department_id" in update_dict and update_dict["department_id"] != emp.department_id:
            await self._validate_department(update_dict["department_id"])

        # Manager check & circular reporting
        if "manager_id" in update_dict and update_dict["manager_id"] != emp.manager_id:
            new_manager_id = update_dict["manager_id"]
            if new_manager_id:
                mgr = await self.repo.get_by_id(self.db, new_manager_id)
                if not mgr or mgr.is_deleted:
                    raise ApnaERPException(
                        message=f"Manager with ID '{new_manager_id}' not found.",
                        status_code=404,
                        error_code="MANAGER_NOT_FOUND"
                    )
            await self._validate_no_circular_manager(employee_id, new_manager_id)

        # User ID check
        if "user_id" in update_dict and update_dict["user_id"] != emp.user_id:
            new_user_id = update_dict["user_id"]
            if new_user_id:
                linked_user = await self.user_repo.get_by_id(self.db, new_user_id)
                if not linked_user:
                    raise ApnaERPException(
                        message=f"User with ID '{new_user_id}' not found.",
                        status_code=404,
                        error_code="USER_NOT_FOUND"
                    )
                if await self.repo.exists_by_user_id(self.db, new_user_id, exclude_id=employee_id):
                    raise ApnaERPException(
                        message=f"User ID '{new_user_id}' is already linked to another employee.",
                        status_code=400,
                        error_code="USER_ALREADY_LINKED"
                    )

        # Profile photo file check
        if "profile_photo_file_id" in update_dict and update_dict["profile_photo_file_id"] != emp.profile_photo_file_id:
            file_id = update_dict["profile_photo_file_id"]
            if file_id:
                profile_file = await self.file_repo.get_by_id(self.db, file_id)
                if not profile_file:
                    raise ApnaERPException(
                        message=f"File with ID '{file_id}' not found.",
                        status_code=404,
                        error_code="FILE_NOT_FOUND"
                    )

        updated_emp = await self.repo.update(self.db, db_obj=emp, obj_in=data)

        # Audit Log
        await log_audit(
            db=self.db,
            action="EMPLOYEE_UPDATE",
            entity_type="Employee",
            entity_id=str(employee_id),
            user_id=current_user.id if current_user else None,
            username=current_user.username if current_user else None,
            previous_data=prev_data,
            new_data={
                "code": updated_emp.employee_code,
                "email": updated_emp.work_email,
                "department_id": str(updated_emp.department_id),
            },
            status_code=200,
        )

        # Invalidate Cache
        await self._invalidate_employee_caches(department_id=updated_emp.department_id)

        # Dispatch background notification
        try:
            send_employee_notification_task.delay(
                event="EMPLOYEE_UPDATE",
                employee_id=str(updated_emp.id),
                code=updated_emp.employee_code,
                email=updated_emp.work_email,
            )
        except Exception as e:
            logger.warning(f"[EmployeeService] Celery task enqueue failed: {e}")

        return updated_emp

    async def delete_employee(
        self, employee_id: uuid.UUID, current_user: Optional[User] = None, request: Optional[Request] = None
    ) -> Employee:
        """Soft deletes an employee."""
        emp = await self.get_employee_by_id(employee_id)

        await self.repo.soft_delete(self.db, id=employee_id)
        deleted_emp = await self.repo.get_by_id(self.db, employee_id, include_deleted=True)

        # Audit Log
        await log_audit(
            db=self.db,
            action="EMPLOYEE_DELETE",
            entity_type="Employee",
            entity_id=str(employee_id),
            user_id=current_user.id if current_user else None,
            username=current_user.username if current_user else None,
            previous_data={"code": emp.employee_code, "email": emp.work_email},
            new_data={"is_deleted": True},
            status_code=200,
        )

        # Invalidate Cache
        await self._invalidate_employee_caches(department_id=emp.department_id)

        # Dispatch background notification
        try:
            send_employee_notification_task.delay(
                event="EMPLOYEE_DELETE",
                employee_id=str(emp.id),
                code=emp.employee_code,
                email=emp.work_email,
            )
        except Exception as e:
            logger.warning(f"[EmployeeService] Celery task enqueue failed: {e}")

        return deleted_emp

    async def restore_employee(
        self, employee_id: uuid.UUID, current_user: Optional[User] = None, request: Optional[Request] = None
    ) -> Employee:
        """Restores a soft-deleted employee."""
        emp = await self.repo.get_by_id(self.db, employee_id, include_deleted=True)
        if not emp:
            raise ApnaERPException(
                message=f"Employee with ID '{employee_id}' not found.",
                status_code=404,
                error_code="EMPLOYEE_NOT_FOUND"
            )

        if not emp.is_deleted:
            raise ApnaERPException(
                message="Employee is not deleted.",
                status_code=400,
                error_code="NOT_DELETED_ERROR"
            )

        await self.repo.restore(self.db, id=employee_id)
        restored_emp = await self.repo.get_by_id(self.db, employee_id)

        # Audit Log
        await log_audit(
            db=self.db,
            action="EMPLOYEE_RESTORE",
            entity_type="Employee",
            entity_id=str(employee_id),
            user_id=current_user.id if current_user else None,
            username=current_user.username if current_user else None,
            previous_data={"is_deleted": True},
            new_data={"is_deleted": False},
            status_code=200,
        )

        # Invalidate Cache
        await self._invalidate_employee_caches(department_id=restored_emp.department_id)

        return restored_emp
