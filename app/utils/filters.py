from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel
from sqlalchemy import Select, func


class FilterOperator(str, Enum):
    EQ = "eq"
    NEQ = "neq"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    LIKE = "like"
    ILIKE = "ilike"
    IN = "in"
    NOT_IN = "not_in"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


class FilterCriterion(BaseModel):
    """
    Structured filter criterion for dynamic SQL querying.
    """
    field: str
    operator: FilterOperator = FilterOperator.EQ
    value: Optional[Any] = None


def apply_filters(query: Select, model: Any, filters: Optional[List[FilterCriterion]]) -> Select:
    """
    Dynamically applies a list of FilterCriterion objects to a SQLAlchemy Select statement.
    """
    if not filters:
        return query

    for criterion in filters:
        if not hasattr(model, criterion.field):
            continue

        column = getattr(model, criterion.field)
        op = criterion.operator
        val = criterion.value

        if op == FilterOperator.EQ:
            query = query.where(column == val)
        elif op == FilterOperator.NEQ:
            query = query.where(column != val)
        elif op == FilterOperator.GT:
            query = query.where(column > val)
        elif op == FilterOperator.GTE:
            query = query.where(column >= val)
        elif op == FilterOperator.LT:
            query = query.where(column < val)
        elif op == FilterOperator.LTE:
            query = query.where(column <= val)
        elif op == FilterOperator.LIKE:
            query = query.where(column.like(f"%{val}%"))
        elif op == FilterOperator.ILIKE:
            query = query.where(column.ilike(f"%{val}%"))
        elif op == FilterOperator.IN:
            if isinstance(val, (list, tuple, set)):
                query = query.where(column.in_(val))
        elif op == FilterOperator.NOT_IN:
            if isinstance(val, (list, tuple, set)):
                query = query.where(~column.in_(val))
        elif op == FilterOperator.IS_NULL:
            query = query.where(column.is_(None))
        elif op == FilterOperator.IS_NOT_NULL:
            query = query.where(column.isnot(None))

    return query
