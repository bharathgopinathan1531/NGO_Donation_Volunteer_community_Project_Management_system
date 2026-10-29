from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class AllocationCreate(BaseModel):
    resource_id: int
    project_id: int
    quantity: int = Field(gt=0)
    notes: str | None = Field(default=None, max_length=255)


class AllocationOut(ORMModel):
    id: int
    resource_id: int
    project_id: int
    quantity: int
    notes: str | None
    allocated_by: int | None
    allocated_at: datetime
    distributed_quantity: int = 0
