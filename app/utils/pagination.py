import math
from typing import Generic, List, TypeVar
from pydantic import BaseModel, ConfigDict, Field

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


class PaginatedResult(BaseModel, Generic[T]):
    """
    Container holding paginated query results and metadata.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool

    def __init__(self, items: List[T], total: int, page: int, page_size: int, **data):
        total_pages = data.pop("total_pages", math.ceil(total / page_size) if page_size > 0 else 0)
        has_next = data.pop("has_next", page < total_pages)
        has_prev = data.pop("has_prev", page > 1)
        super().__init__(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev,
            **data,
        )


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
