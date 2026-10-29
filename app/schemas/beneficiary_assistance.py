from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class AssistanceCreate(BaseModel):
    beneficiary_id: int
    project_id: int
    resource_id: int | None = None
    assistance_type: str = Field(min_length=2, max_length=100)
    quantity: int = Field(default=0, ge=0)
    distribution_date: date
    description: str | None = None


class AssistanceOut(ORMModel):
    id: int
    beneficiary_id: int
    project_id: int
    resource_id: int | None
    assistance_type: str
    quantity: int
    distribution_date: date
    description: str | None
    recorded_by: int | None
    created_at: datetime
