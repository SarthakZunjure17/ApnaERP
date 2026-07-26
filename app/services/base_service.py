import logging
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.exceptions.base import NotFoundException
from app.repositories.base_repository import BaseRepository
from app.utils.filters import FilterCriterion
from app.utils.pagination import PaginatedResult, PaginationParams
from app.utils.sorting import SortCriterion

logger = logging.getLogger("app.services")

RepoType = TypeVar("RepoType", bound=BaseRepository)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseService(Generic[RepoType]):
    """
    Generic Base Service layer establishing business logic guidelines and wrapping
    the underlying BaseRepository layer.
    """
    def __init__(self, repository: RepoType):
        self.repository = repository

    async def get_by_id(
        self, db: AsyncSession, id: Any, include_deleted: bool = False
    ) -> Any:
        """
        Retrieves an entity by ID or raises NotFoundException if missing.
        """
        item = await self.repository.get_by_id(db, id, include_deleted=include_deleted)
        if not item:
            raise NotFoundException(message=f"{self.repository.model.__name__} with ID '{id}' not found.")
        return item

    async def get_all(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
    ) -> List[Any]:
        """
        Retrieves all entities with skip/limit pagination.
        """
        return await self.repository.get_all(db, skip=skip, limit=limit, include_deleted=include_deleted)

    async def get_paginated(
        self,
        db: AsyncSession,
        *,
        params: PaginationParams,
        filters: Optional[List[FilterCriterion]] = None,
        sorting: Optional[List[SortCriterion]] = None,
        search_term: Optional[str] = None,
        search_fields: Optional[List[str]] = None,
        include_deleted: bool = False,
    ) -> PaginatedResult[Any]:
        """
        Retrieves paginated records with dynamic filtering, sorting, and search.
        """
        return await self.repository.get_multi_paginated(
            db,
            params=params,
            filters=filters,
            sorting=sorting,
            search_term=search_term,
            search_fields=search_fields,
            include_deleted=include_deleted,
        )

    async def create(
        self, db: AsyncSession, *, obj_in: Union[Any, Dict[str, Any]]
    ) -> Any:
        """
        Creates a new entity record via repository.
        """
        return await self.repository.create(db, obj_in=obj_in)

    async def update(
        self,
        db: AsyncSession,
        *,
        id: Any,
        obj_in: Union[Any, Dict[str, Any]],
    ) -> Any:
        """
        Updates an existing entity record or raises NotFoundException.
        """
        db_obj = await self.get_by_id(db, id, include_deleted=True)
        return await self.repository.update(db, db_obj=db_obj, obj_in=obj_in)

    async def delete(self, db: AsyncSession, *, id: Any) -> None:
        """
        Hard deletes an entity record or raises NotFoundException.
        """
        deleted = await self.repository.delete(db, id=id)
        if not deleted:
            raise NotFoundException(message=f"{self.repository.model.__name__} with ID '{id}' not found.")

    async def soft_delete(self, db: AsyncSession, *, id: Any) -> None:
        """
        Soft deletes an entity record or raises NotFoundException.
        """
        soft_deleted = await self.repository.soft_delete(db, id=id)
        if not soft_deleted:
            raise NotFoundException(message=f"{self.repository.model.__name__} with ID '{id}' not found or already deleted.")

    async def restore(self, db: AsyncSession, *, id: Any) -> Any:
        """
        Restores a soft-deleted record or raises NotFoundException.
        """
        restored = await self.repository.restore(db, id=id)
        if not restored:
            raise NotFoundException(message=f"Soft-deleted {self.repository.model.__name__} with ID '{id}' not found.")
        return await self.get_by_id(db, id)

    async def exists(self, db: AsyncSession, id: Any, include_deleted: bool = False) -> bool:
        """
        Checks whether an entity record exists by ID.
        """
        return await self.repository.exists(db, id, include_deleted=include_deleted)

    async def count(
        self,
        db: AsyncSession,
        filters: Optional[List[FilterCriterion]] = None,
        include_deleted: bool = False,
    ) -> int:
        """
        Returns count of entity records matching optional filters.
        """
        return await self.repository.count(db, filters=filters, include_deleted=include_deleted)
