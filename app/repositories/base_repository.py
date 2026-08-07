from decimal import Decimal
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.filters import FilterCriterion, apply_filters
from app.utils.pagination import PaginatedResult, PaginationParams
from app.utils.search import apply_search
from app.utils.sorting import SortCriterion, apply_sorting

logger = logging.getLogger("app.repositories")

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Generic Base Repository implementing standard CRUD operations, soft deletion,
    restoration, pagination, filtering, sorting, and multi-column searching.
    """
    def __init__(self, model: Type[ModelType]):
        self.model = model

    def _apply_soft_delete_filter(self, query: Any, include_deleted: bool = False) -> Any:
        """
        Helper method to apply soft-delete filter if the model inherits SoftDeleteMixin.
        """
        if not include_deleted and hasattr(self.model, "is_deleted"):
            query = query.where(getattr(self.model, "is_deleted") == False)
        return query

    async def get_by_id(
        self, db: AsyncSession, id: Any, include_deleted: bool = False
    ) -> Optional[ModelType]:
        """
        Retrieves a single entity record by Primary Key ID.
        """
        logger.debug(f"[{self.model.__name__}] Repository get_by_id: {id}")
        query = select(self.model).where(getattr(self.model, "id") == id)
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)
        result = await db.execute(query)
        return result.unique().scalars().first()

    async def get_all(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
    ) -> List[ModelType]:
        """
        Retrieves all entity records with skip and limit offset.
        """
        logger.debug(f"[{self.model.__name__}] Repository get_all (skip={skip}, limit={limit})")
        query = select(self.model)
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.unique().scalars().all())

    async def get_multi_paginated(
        self,
        db: AsyncSession,
        *,
        params: PaginationParams,
        filters: Optional[List[FilterCriterion]] = None,
        sorting: Optional[List[SortCriterion]] = None,
        search_term: Optional[str] = None,
        search_fields: Optional[List[str]] = None,
        include_deleted: bool = False,
    ) -> PaginatedResult[ModelType]:
        """
        Retrieves a paginated result set with dynamic filtering, sorting, and search.
        """
        logger.debug(f"[{self.model.__name__}] Repository get_multi_paginated (page={params.page}, size={params.page_size})")
        base_query = select(self.model)
        base_query = self._apply_soft_delete_filter(base_query, include_deleted=include_deleted)

        # Apply filtering, search, sorting
        base_query = apply_filters(base_query, self.model, filters)
        base_query = apply_search(base_query, self.model, search_term, search_fields)
        
        # Calculate total matching count
        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await db.execute(count_query)
        total = count_result.scalar_one_or_none() or 0

        # Apply sorting and pagination offsets
        paginated_query = apply_sorting(base_query, self.model, sorting)
        paginated_query = paginated_query.offset(params.offset).limit(params.page_size)

        result = await db.execute(paginated_query)
        items = list(result.unique().scalars().all())

        return PaginatedResult(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    async def create(self, db: AsyncSession, *, obj_in: Union[CreateSchemaType, Dict[str, Any]]) -> ModelType:
        """
        Creates a new entity record in the database.
        """
        if isinstance(obj_in, self.model):
            db_obj = obj_in
            create_data = {}
            for c in db_obj.__table__.columns:
                if hasattr(db_obj, c.name):
                    val = getattr(db_obj, c.name)
                    if isinstance(val, (dict, list, int, float, bool, type(None))):
                        create_data[c.name] = val
                    elif isinstance(val, Decimal):
                        create_data[c.name] = float(val)
                    else:
                        create_data[c.name] = str(val)
        elif isinstance(obj_in, dict):
            create_data = obj_in
            db_obj = self.model(**create_data)
        else:
            create_data = obj_in.model_dump(exclude_unset=True)
            db_obj = self.model(**create_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        logger.info(f"[{self.model.__name__}] Created record ID '{getattr(db_obj, 'id', None)}'")

        # Record Audit Log for non-AuditLog models
        if self.model.__name__ != "AuditLog":
            from app.utils.audit import log_audit
            await log_audit(
                db,
                action="CREATE",
                entity_type=self.model.__name__,
                entity_id=getattr(db_obj, "id", None),
                new_data=create_data,
                status_code=201,
            )

        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]],
    ) -> ModelType:
        """
        Updates an existing entity record in the database.
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        prev_data = {}
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                prev_data[field] = getattr(db_obj, field)
                setattr(db_obj, field, value)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        logger.info(f"[{self.model.__name__}] Updated record ID '{getattr(db_obj, 'id', None)}'")

        if self.model.__name__ != "AuditLog":
            from app.utils.audit import log_audit
            await log_audit(
                db,
                action="UPDATE",
                entity_type=self.model.__name__,
                entity_id=getattr(db_obj, "id", None),
                previous_data=prev_data,
                new_data=update_data,
                status_code=200,
            )

        return db_obj

    async def delete(self, db: AsyncSession, *, id: Any) -> bool:
        """
        Performs a hard physical deletion of an entity record from the database.
        """
        db_obj = await self.get_by_id(db, id, include_deleted=True)
        if not db_obj:
            return False
        await db.delete(db_obj)
        await db.commit()
        logger.info(f"[{self.model.__name__}] Hard deleted record ID '{id}'")

        if self.model.__name__ != "AuditLog":
            from app.utils.audit import log_audit
            await log_audit(
                db,
                action="DELETE",
                entity_type=self.model.__name__,
                entity_id=id,
                status_code=200,
            )

        return True

    async def soft_delete(self, db: AsyncSession, *, id: Any) -> bool:
        """
        Performs a soft deletion by setting is_deleted=True and timestamping deleted_at.
        """
        db_obj = await self.get_by_id(db, id, include_deleted=False)
        if not db_obj or not hasattr(db_obj, "is_deleted"):
            return False

        setattr(db_obj, "is_deleted", True)
        if hasattr(db_obj, "deleted_at"):
            setattr(db_obj, "deleted_at", datetime.now(timezone.utc))

        db.add(db_obj)
        await db.commit()
        logger.info(f"[{self.model.__name__}] Soft deleted record ID '{id}'")

        if self.model.__name__ != "AuditLog":
            from app.utils.audit import log_audit
            await log_audit(
                db,
                action="SOFT_DELETE",
                entity_type=self.model.__name__,
                entity_id=id,
                status_code=200,
            )

        return True

    async def restore(self, db: AsyncSession, *, id: Any) -> bool:
        """
        Restores a soft-deleted record by clearing is_deleted and deleted_at flags.
        """
        db_obj = await self.get_by_id(db, id, include_deleted=True)
        if not db_obj or not hasattr(db_obj, "is_deleted") or not getattr(db_obj, "is_deleted"):
            return False

        setattr(db_obj, "is_deleted", False)
        if hasattr(db_obj, "deleted_at"):
            setattr(db_obj, "deleted_at", None)

        db.add(db_obj)
        await db.commit()
        logger.info(f"[{self.model.__name__}] Restored soft-deleted record ID '{id}'")

        if self.model.__name__ != "AuditLog":
            from app.utils.audit import log_audit
            await log_audit(
                db,
                action="RESTORE",
                entity_type=self.model.__name__,
                entity_id=id,
                status_code=200,
            )

        return True

    async def exists(self, db: AsyncSession, id: Any, include_deleted: bool = False) -> bool:
        """
        Checks whether an entity record exists by Primary Key ID.
        """
        query = select(func.count()).select_from(self.model).where(getattr(self.model, "id") == id)
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)
        result = await db.execute(query)
        count = result.scalar_one_or_none() or 0
        return count > 0

    async def count(
        self,
        db: AsyncSession,
        filters: Optional[List[FilterCriterion]] = None,
        include_deleted: bool = False,
    ) -> int:
        """
        Returns the total count of entity records matching optional filters.
        """
        query = select(self.model)
        query = self._apply_soft_delete_filter(query, include_deleted=include_deleted)
        query = apply_filters(query, self.model, filters)

        count_query = select(func.count()).select_from(query.subquery())
        result = await db.execute(count_query)
        return result.scalar_one_or_none() or 0
