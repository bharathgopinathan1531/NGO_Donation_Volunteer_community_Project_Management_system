from dataclasses import dataclass
from typing import Iterable, Literal

from fastapi import Query
from sqlalchemy import Select, asc, desc

from app.core.exceptions import BadRequestError


@dataclass
class SortParams:
    sort_by: str | None = None
    order: Literal["asc", "desc"] = "asc"


def sort_params(
    sort_by: str | None = Query(None, description="Field to sort by"),
    order: Literal["asc", "desc"] = Query("asc", description="Sort direction"),
) -> SortParams:
    return SortParams(sort_by=sort_by, order=order)


def apply_sorting(stmt: Select, model, sort: SortParams, allowed: Iterable[str], default: str = "id", default_order: str = "asc") -> Select:
    allowed = set(allowed)
    field = sort.sort_by or default
    direction = sort.order if sort.sort_by else default_order
    if field not in allowed:
        raise BadRequestError(f"Cannot sort by '{field}'. Allowed: {', '.join(sorted(allowed))}")
    column = getattr(model, field)
    primary = desc(column) if direction == "desc" else asc(column)
    tiebreak = getattr(model, "id", None)
    return stmt.order_by(primary, tiebreak) if tiebreak is not None and field != "id" else stmt.order_by(primary)
