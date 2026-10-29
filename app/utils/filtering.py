from datetime import date, datetime, time
from typing import Iterable

from sqlalchemy import Select, or_


def apply_equals(stmt: Select, model, **filters) -> Select:
    for name, value in filters.items():
        if value is not None:
            stmt = stmt.where(getattr(model, name) == value)
    return stmt


def apply_date_range(stmt: Select, column, date_from: date | None, date_to: date | None) -> Select:
    """Inclusive range; works for both DATE and DATETIME columns."""
    is_datetime = getattr(column.type, "python_type", None) is datetime
    if date_from is not None:
        stmt = stmt.where(column >= (datetime.combine(date_from, time.min) if is_datetime else date_from))
    if date_to is not None:
        stmt = stmt.where(column <= (datetime.combine(date_to, time.max) if is_datetime else date_to))
    return stmt


def apply_search(stmt: Select, columns: Iterable, term: str | None) -> Select:
    if term and term.strip():
        like = f"%{term.strip()}%"
        stmt = stmt.where(or_(*[c.ilike(like) for c in columns]))
    return stmt
