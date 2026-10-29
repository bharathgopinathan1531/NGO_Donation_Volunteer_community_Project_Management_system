from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel
from app.utils.enums import VolunteerStatus

PHONE_PATTERN = r"^[0-9+\-() ]{6,30}$"


class VolunteerCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str | None = Field(default=None, pattern=PHONE_PATTERN)
    address: str | None = None
    skills: list[str] = Field(default_factory=list)
    experience: str | None = None
    availability: str | None = Field(default=None, max_length=255)
    emergency_contact_name: str | None = Field(default=None, max_length=150)
    emergency_contact_phone: str | None = Field(default=None, pattern=PHONE_PATTERN)
    emergency_contact_relation: str | None = Field(default=None, max_length=50)
    user_id: int | None = None  # staff may link an existing user account


class VolunteerUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    phone: str | None = Field(default=None, pattern=PHONE_PATTERN)
    address: str | None = None
    skills: list[str] | None = None
    experience: str | None = None
    availability: str | None = Field(default=None, max_length=255)
    status: VolunteerStatus | None = None
    emergency_contact_name: str | None = Field(default=None, max_length=150)
    emergency_contact_phone: str | None = Field(default=None, pattern=PHONE_PATTERN)
    emergency_contact_relation: str | None = Field(default=None, max_length=50)


class VolunteerOut(ORMModel):
    id: int
    user_id: int | None
    full_name: str
    email: str
    phone: str | None
    address: str | None
    skills: list[str]
    experience: str | None
    availability: str | None
    status: VolunteerStatus
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    emergency_contact_relation: str | None
    created_at: datetime
    updated_at: datetime
