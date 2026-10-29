import math
from dataclasses import dataclass
from typing import Any

from fastapi import Query
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session


@dataclass
class PaginationParams:
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def pagination_params(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=200, description="Items per page"),
) -> PaginationParams:
    return PaginationParams(page=page, page_size=page_size)


def paginate(db: Session, stmt: Select, params: PaginationParams) -> tuple[list[Any], int]:
    """Run an ORM entity select with LIMIT/OFFSET and return (items, total)."""
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = list(db.scalars(stmt.limit(params.page_size).offset(params.offset)).all())
    return items, total


def build_page(items: list, total: int, params: PaginationParams) -> dict:
    return {
        "items": items,
        "total": total,
        "page": params.page,
        "page_size": params.page_size,
        "pages": math.ceil(total / params.page_size) if params.page_size else 0,
    }
