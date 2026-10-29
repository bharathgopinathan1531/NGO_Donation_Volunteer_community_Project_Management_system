from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel
from app.utils.enums import MilestoneStatus


class MilestoneCreate(BaseModel):
    project_id: int
    title: str = Field(min_length=2, max_length=200)
    description: str | None = None
    due_date: date


class MilestoneUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    due_date: date | None = None
    status: MilestoneStatus | None = None


class MilestoneOut(ORMModel):
    id: int
    project_id: int
    title: str
    description: str | None
    due_date: date
    status: MilestoneStatus
    completed_at: datetime | None
    progress_pct: float = 0.0
    tasks_total: int = 0
    tasks_completed: int = 0
    is_overdue: bool = False
    created_at: datetime
