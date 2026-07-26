from typing import Any, List, Optional
from sqlalchemy import Select, or_


def apply_search(
    query: Select,
    model: Any,
    search_term: Optional[str],
    search_fields: Optional[List[str]] = None,
) -> Select:
    """
    Applies multi-column case-insensitive (ILIKE) search across specified model string fields.
    """
    if not search_term or not search_fields:
        return query

    search_term_clean = f"%{search_term.strip()}%"
    conditions = []

    for field_name in search_fields:
        if hasattr(model, field_name):
            column = getattr(model, field_name)
            conditions.append(column.ilike(search_term_clean))

    if conditions:
        query = query.where(or_(*conditions))

    return query
