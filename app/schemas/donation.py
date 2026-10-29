from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel
from app.utils.enums import DonationMethod, DonationStatus


class DonationCreate(BaseModel):
    donor_id: int
    campaign_id: int
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    donation_date: date
    method: DonationMethod
    reference_number: str = Field(min_length=3, max_length=100)
    status: DonationStatus = DonationStatus.PENDING  # only PENDING or CONFIRMED allowed at creation
    notes: str | None = None

    @field_validator("reference_number")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()

    @field_validator("status")
    @classmethod
    def _initial_status(cls, v: DonationStatus) -> DonationStatus:
        if v not in (DonationStatus.PENDING, DonationStatus.CONFIRMED):
            raise ValueError("A donation can only be created as 'pending' or 'confirmed'")
        return v


class DonationUpdate(BaseModel):
    """Editable fields. Amount/date/method can only change while the donation is pending."""

    amount: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    donation_date: date | None = None
    method: DonationMethod | None = None
    notes: str | None = None


class DonationStatusChange(BaseModel):
    status: DonationStatus
    reason: str | None = Field(default=None, max_length=255)


class DonationOut(ORMModel):
    id: int
    donor_id: int
    campaign_id: int
    amount: Decimal
    donation_date: date
    method: DonationMethod
    reference_number: str
    status: DonationStatus
    notes: str | None
    recorded_by: int | None
    created_at: datetime
    updated_at: datetime
