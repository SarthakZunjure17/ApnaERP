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
