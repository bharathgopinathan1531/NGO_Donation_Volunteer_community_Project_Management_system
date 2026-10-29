from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import ORMModel
from app.utils.enums import ReceiptStatus


class ReceiptCreate(BaseModel):
    donation_id: int


class ReceiptOut(ORMModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    receipt_number: str
    donation_id: int
    donor_id: int
    amount: Decimal
    status: ReceiptStatus
    issued_at: datetime
    issued_by: int | None
    voided_at: datetime | None
    void_reason: str | None
    metadata: dict | None = Field(default=None, validation_alias="meta")
