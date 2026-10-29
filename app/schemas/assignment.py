from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ORMModel
from app.utils.enums import AssignmentStatus


class AssignmentCreate(BaseModel):
    volunteer_id: int
    project_id: int
    responsibility: str = Field(min_length=2, max_length=255)
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def _dates(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class AssignmentUpdate(BaseModel):
    responsibility: str | None = Field(default=None, min_length=2, max_length=255)
    start_date: date | None = None
    end_date: date | None = None


class AssignmentStatusChange(BaseModel):
    status: AssignmentStatus


class AssignmentOut(ORMModel):
    id: int
    volunteer_id: int
    project_id: int
    responsibility: str
    start_date: date
    end_date: date
    status: AssignmentStatus
    hours_completed: Decimal
    assigned_by: int | None
    created_at: datetime
    updated_at: datetime
