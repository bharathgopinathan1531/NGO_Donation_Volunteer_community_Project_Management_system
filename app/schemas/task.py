from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel
from app.utils.enums import TaskPriority, TaskStatus


class TaskCreate(BaseModel):
    milestone_id: int
    title: str = Field(min_length=2, max_length=200)
    description: str | None = None
    assignee_id: int | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    deadline: date


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    assignee_id: int | None = None
    priority: TaskPriority | None = None
    deadline: date | None = None
    status: TaskStatus | None = None
    progress: int | None = Field(default=None, ge=0, le=100)


class TaskOut(ORMModel):
    id: int
    milestone_id: int
    title: str
    description: str | None
    assignee_id: int | None
    priority: TaskPriority
    status: TaskStatus
    progress: int
    deadline: date
    is_overdue: bool = False
    created_at: datetime
    updated_at: datetime
