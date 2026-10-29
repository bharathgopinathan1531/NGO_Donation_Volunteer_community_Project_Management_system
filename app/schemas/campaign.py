from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ORMModel
from app.utils.enums import CampaignCategory, CampaignStatus


class CampaignCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str | None = None
    category: CampaignCategory = CampaignCategory.OTHER
    goal_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    start_date: date
    end_date: date
    manager_id: int | None = None

    @model_validator(mode="after")
    def _dates(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class CampaignUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = None
    category: CampaignCategory | None = None
    goal_amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    start_date: date | None = None
    end_date: date | None = None
    manager_id: int | None = None


class CampaignOut(ORMModel):
    id: int
    title: str
    description: str | None
    category: CampaignCategory
    status: CampaignStatus
    goal_amount: Decimal
    raised_amount: Decimal
    achievement_pct: float = 0.0
    remaining_amount: Decimal = Decimal("0.00")
    start_date: date
    end_date: date
    manager_id: int | None
    created_at: datetime
    updated_at: datetime
