from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel
from sqlalchemy import Select, asc, desc


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class SortCriterion(BaseModel):
    """
    Structured sorting criterion for dynamic SQL ordering.
    """
    field: str
    order: SortOrder = SortOrder.ASC


def apply_sorting(query: Select, model: Any, sorting: Optional[List[SortCriterion]]) -> Select:
    """
    Dynamically applies a list of SortCriterion objects to a SQLAlchemy Select statement.
    """
    if not sorting:
        return query

    order_clauses = []
    for criterion in sorting:
        if not hasattr(model, criterion.field):
            continue
        column = getattr(model, criterion.field)
        if criterion.order == SortOrder.DESC:
            order_clauses.append(desc(column))
        else:
            order_clauses.append(asc(column))

    if order_clauses:
        query = query.order_by(*order_clauses)

    return query

def parse_sort_query(sort_str: Optional[str]) -> Optional[List[SortCriterion]]:
    """
    Parses a sort query string (e.g. "code,-created_at") into a list of SortCriterion objects.
    """
    if not sort_str:
        return None
    criteria = []
    for item in sort_str.split(","):
        item = item.strip()
        if not item:
            continue
        if item.startswith("-"):
            criteria.append(SortCriterion(field=item[1:], order=SortOrder.DESC))
        elif ":" in item:
            parts = item.split(":", 1)
            order = SortOrder.DESC if parts[1].lower() == "desc" else SortOrder.ASC
            criteria.append(SortCriterion(field=parts[0], order=order))
        else:
            criteria.append(SortCriterion(field=item, order=SortOrder.ASC))
    return criteria if criteria else None

