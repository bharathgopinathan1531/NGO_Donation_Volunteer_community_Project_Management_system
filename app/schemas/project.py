from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ORMModel
from app.utils.enums import ProjectStatus


class ProjectCreate(BaseModel):
    name: str = Field(min_length=3, max_length=200)
    description: str | None = None
    objectives: str | None = None
    location: str | None = Field(default=None, max_length=255)
    start_date: date
    end_date: date
    budget: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    manager_id: int | None = None
    campaign_id: int | None = None

    @model_validator(mode="after")
    def _dates(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = None
    objectives: str | None = None
    location: str | None = Field(default=None, max_length=255)
    start_date: date | None = None
    end_date: date | None = None
    budget: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    manager_id: int | None = None
    campaign_id: int | None = None


class ProjectStatusChange(BaseModel):
    status: ProjectStatus


class ProjectOut(ORMModel):
    id: int
    name: str
    description: str | None
    objectives: str | None
    location: str | None
    start_date: date
    end_date: date
    budget: Decimal
    status: ProjectStatus
    manager_id: int | None
    campaign_id: int | None
    created_at: datetime
    updated_at: datetime


class ProjectDetail(ProjectOut):
    milestones_total: int = 0
    milestones_completed: int = 0
    milestone_completion_pct: float = 0.0
    approval_state: str | None = None  # latest approval action: submitted / approved / rejected / None
