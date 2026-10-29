from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel
from app.utils.enums import DonorStatus, DonorType


class DonorBase(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    donor_type: DonorType = DonorType.INDIVIDUAL
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30, pattern=r"^[0-9+\-() ]{6,30}$")
    address: str | None = None
    city: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    tax_id: str | None = Field(default=None, max_length=50)
    contact_person: str | None = Field(default=None, max_length=150)
    notes: str | None = None


class DonorCreate(DonorBase):
    status: DonorStatus = DonorStatus.ACTIVE
    user_id: int | None = None


class DonorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    donor_type: DonorType | None = None
    status: DonorStatus | None = None
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30, pattern=r"^[0-9+\-() ]{6,30}$")
    address: str | None = None
    city: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    tax_id: str | None = Field(default=None, max_length=50)
    contact_person: str | None = Field(default=None, max_length=150)
    notes: str | None = None


class DonorOut(ORMModel):
    id: int
    user_id: int | None
    name: str
    donor_type: DonorType
    status: DonorStatus
    email: str | None
    phone: str | None
    address: str | None
    city: str | None
    country: str | None
    tax_id: str | None
    contact_person: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
