from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class ImpactUpdateCreate(BaseModel):
    """Any metric left empty is computed from database records at submission time."""

    project_id: int
    beneficiaries_served: int | None = Field(default=None, ge=0)
    volunteer_hours: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    resources_distributed: int | None = Field(default=None, ge=0)
    funds_utilized: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    milestones_achieved: int | None = Field(default=None, ge=0)
    notes: str | None = None


class ImpactUpdateOut(ORMModel):
    id: int
    project_id: int
    beneficiaries_served: int
    volunteer_hours: Decimal
    resources_distributed: int
    funds_utilized: Decimal
    milestones_achieved: int
    project_completed: bool
    notes: str | None
    submitted_by: int | None
    created_at: datetime


class ImpactSummary(BaseModel):
    """Live metrics computed from database records."""

    project_id: int | None = None
    beneficiaries_served: int
    volunteer_hours: Decimal
    resources_distributed: int
    projects_completed: int
    funds_utilized: Decimal
    milestones_achieved: int
