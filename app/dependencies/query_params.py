from typing import List, Optional
from fastapi import Query
from pydantic import BaseModel, Field
from app.utils.filters import FilterCriterion
from app.utils.pagination import PaginationParams
from app.utils.sorting import SortCriterion, SortOrder


class CommonQueryParams(BaseModel):
    """
    Common query parameters container for API endpoints.
    """
    pagination: PaginationParams
    sorting: Optional[List[SortCriterion]] = None
    search_term: Optional[str] = None


def get_pagination_params(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page (max 100)"),
) -> PaginationParams:
    """
    Dependency provider for pagination parameters.
    """
    return PaginationParams(page=page, page_size=page_size)


def get_sorting_params(
    sort_by: Optional[str] = Query(default=None, description="Field name to sort by"),
    order: SortOrder = Query(default=SortOrder.ASC, description="Sort direction ('asc' or 'desc')"),
) -> Optional[List[SortCriterion]]:
    """
    Dependency provider for sorting parameters.
    """
    if not sort_by:
        return None
    return [SortCriterion(field=sort_by, order=order)]


def get_search_params(
    q: Optional[str] = Query(default=None, description="Search query string"),
) -> Optional[str]:
    """
    Dependency provider for search query string.
    """
    return q
