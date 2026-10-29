from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel
from app.utils.enums import StockTransactionType


class StockMovement(BaseModel):
    quantity: int = Field(gt=0)
    reason: str | None = Field(default=None, max_length=255)
    reference: str | None = Field(default=None, max_length=100)


class StockOutMovement(StockMovement):
    reason: str = Field(min_length=3, max_length=255)  # mandatory for stock-out


class StockTransactionOut(ORMModel):
    id: int
    resource_id: int
    transaction_type: StockTransactionType
    quantity: int
    balance_after: int
    project_id: int | None
    reason: str | None
    reference: str | None
    created_by: int | None
    created_at: datetime
