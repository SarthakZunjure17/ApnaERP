import uuid
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file import File
from app.repositories.base_repository import BaseRepository
from app.schemas.file import FileCreate
from app.utils.pagination import PaginatedResult, PaginationParams
from app.utils.search import apply_search
from app.utils.sorting import SortCriterion, SortOrder, apply_sorting


class FileRepository(BaseRepository[File, FileCreate, FileCreate]):
    """
    Repository layer for File entity.
    """
    def __init__(self):
        super().__init__(File)

    async def get_by_checksum(self, db: AsyncSession, checksum: str) -> Optional[File]:
        """
        Retrieves an existing File record matching SHA256 checksum (duplicate detection).
        """
        result = await db.execute(select(File).where(File.checksum == checksum))
        return result.scalars().first()

    async def get_by_entity(
        self,
        db: AsyncSession,
        *,
        entity_type: str,
        entity_id: str,
        params: PaginationParams,
    ) -> PaginatedResult[File]:
        """
        Retrieves files attached to a specific entity type and entity ID.
        """
        query = select(File).where(
            func.lower(File.entity_type) == entity_type.lower(),
            File.entity_id == entity_id,
        )

        count_query = select(func.count()).select_from(query.subquery())
        count_res = await db.execute(count_query)
        total = count_res.scalar_one_or_none() or 0

        paginated_query = query.order_by(File.created_at.desc()).offset(params.offset).limit(params.page_size)
        result = await db.execute(paginated_query)
        items = list(result.scalars().all())

        return PaginatedResult(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
        )

    async def get_filtered_files(
        self,
        db: AsyncSession,
        *,
        params: PaginationParams,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        uploaded_by_id: Optional[uuid.UUID] = None,
        search_term: Optional[str] = None,
        sorting: Optional[List[SortCriterion]] = None,
    ) -> PaginatedResult[File]:
        """
        Retrieves paginated file records with filtering and original filename searching.
        """
        query = select(File)

        if entity_type:
            query = query.where(func.lower(File.entity_type) == entity_type.lower())
        if entity_id:
            query = query.where(File.entity_id == entity_id)
        if uploaded_by_id:
            query = query.where(File.uploaded_by_id == uploaded_by_id)

        query = apply_search(query, File, search_term, search_fields=["original_filename", "stored_filename"])

        count_query = select(func.count()).select_from(query.subquery())
        count_res = await db.execute(count_query)
        total = count_res.scalar_one_or_none() or 0

        if not sorting:
            sorting = [SortCriterion(field="created_at", order=SortOrder.DESC)]

        paginated_query = apply_sorting(query, File, sorting)
        paginated_query = paginated_query.offset(params.offset).limit(params.page_size)

        result = await db.execute(paginated_query)
        items = list(result.scalars().all())

        return PaginatedResult(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
        )


file_repository = FileRepository()
