from typing import Any

from pydantic import BaseModel


class ReportPage(BaseModel):
    report: str
    columns: list[str]
    rows: list[dict[str, Any]]
    total: int
    page: int
    page_size: int
    pages: int
