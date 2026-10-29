from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ORMModel
from app.utils.enums import ExpenseCategory, ExpenseStatus


class ExpenseCreate(BaseModel):
    project_id: int
    category: ExpenseCategory
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    expense_date: date
    description: str = Field(min_length=3)
    receipt_reference: str | None = Field(default=None, max_length=255)
    attachment_url: str | None = Field(default=None, max_length=500, pattern=r"^https?://")

    @model_validator(mode="after")
    def _proof(self):
        if not self.receipt_reference and not self.attachment_url:
            raise ValueError("Provide a receipt_reference or an attachment_url")
        return self


class ExpenseUpdate(BaseModel):
    """Only submitted (not yet reviewed) expenses can be edited."""

    category: ExpenseCategory | None = None
    amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    expense_date: date | None = None
    description: str | None = Field(default=None, min_length=3)
    receipt_reference: str | None = Field(default=None, max_length=255)
    attachment_url: str | None = Field(default=None, max_length=500, pattern=r"^https?://")


class ExpenseApprove(BaseModel):
    comment: str | None = Field(default=None, max_length=1000)
    override_budget: bool = False  # super admin only: approve even if it exceeds the project budget


class ExpenseReject(BaseModel):
    comment: str = Field(min_length=3, max_length=1000)


class ExpenseOut(ORMModel):
    id: int
    project_id: int
    category: ExpenseCategory
    amount: Decimal
    expense_date: date
    description: str
    receipt_reference: str | None
    attachment_url: str | None
    status: ExpenseStatus
    submitted_by: int | None
    reviewed_by: int | None
    reviewed_at: datetime | None
    review_comment: str | None
    created_at: datetime
