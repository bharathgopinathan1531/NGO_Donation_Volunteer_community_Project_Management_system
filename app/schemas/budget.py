from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ORMModel
from app.utils.enums import BudgetScope


class BudgetSet(BaseModel):
    """Create or replace the budget of a campaign or a project."""

    scope: BudgetScope
    campaign_id: int | None = None
    project_id: int | None = None
    amount: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    notes: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def _target(self):
        if self.scope == BudgetScope.CAMPAIGN and (self.campaign_id is None or self.project_id is not None):
            raise ValueError("campaign budgets need campaign_id (and no project_id)")
        if self.scope == BudgetScope.PROJECT and (self.project_id is None or self.campaign_id is not None):
            raise ValueError("project budgets need project_id (and no campaign_id)")
        return self


class BudgetOut(ORMModel):
    id: int
    campaign_id: int | None
    project_id: int | None
    amount: Decimal
    notes: str | None
    created_at: datetime
    updated_at: datetime


class BudgetUtilization(BaseModel):
    scope: BudgetScope
    entity_id: int
    entity_name: str
    budget: Decimal
    spent: Decimal  # approved + reimbursed expenses
    pending: Decimal  # submitted, not yet decided
    remaining: Decimal
    utilization_pct: float
    is_overrun: bool
    overrun_amount: Decimal
