from typing import Any, Generic, List, Optional, Type, TypeVar
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Abstract Base Repository enforcing Clean Architecture data access contract.
    All entity-specific repositories will inherit from this class in future phases.
    """
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, id: Any) -> Optional[ModelType]:
        raise NotImplementedError

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        raise NotImplementedError

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        raise NotImplementedError

    async def update(
        self, db: AsyncSession, *, db_obj: ModelType, obj_in: UpdateSchemaType
    ) -> ModelType:
        raise NotImplementedError

    async def remove(self, db: AsyncSession, *, id: Any) -> Optional[ModelType]:
        raise NotImplementedError
