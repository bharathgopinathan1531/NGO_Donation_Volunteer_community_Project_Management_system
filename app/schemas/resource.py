from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel
from app.utils.enums import ResourceCategory


class ResourceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    category: ResourceCategory
    description: str | None = None
    unit: str = Field(default="unit", max_length=30)
    initial_quantity: int = Field(default=0, ge=0)
    low_stock_threshold: int = Field(default=10, ge=0)


class ResourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    category: ResourceCategory | None = None
    description: str | None = None
    unit: str | None = Field(default=None, max_length=30)
    low_stock_threshold: int | None = Field(default=None, ge=0)


class ResourceOut(ORMModel):
    id: int
    name: str
    category: ResourceCategory
    description: str | None
    unit: str
    quantity: int
    low_stock_threshold: int
    is_low_stock: bool = False
    created_at: datetime
    updated_at: datetime
