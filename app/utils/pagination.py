import math
from typing import Generic, List, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """
    Pagination query parameters.
    """
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page (max 100)")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResult(Generic[T]):
    """
    Container holding paginated query results and metadata.
    """
    def __init__(self, items: List[T], total: int, page: int, page_size: int):
        self.items = items
        self.total = total
        self.page = page
        self.page_size = page_size
        self.total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        self.has_next = page < self.total_pages
        self.has_prev = page > 1


def paginate_list(items: List[T], total: int, params: PaginationParams) -> PaginatedResult[T]:
    """
    Helper function to wrap a list of items into a PaginatedResult.
    """
    return PaginatedResult(
        items=items,
        total=total,
        page=params.page,
        page_size=params.page_size,
    )
