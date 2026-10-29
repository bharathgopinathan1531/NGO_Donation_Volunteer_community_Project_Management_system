from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel
from app.utils.enums import BeneficiaryCategory

PHONE_PATTERN = r"^[0-9+\-() ]{6,30}$"


class BeneficiaryCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    category: BeneficiaryCategory
    age: int | None = Field(default=None, ge=0, le=120)
    gender: str | None = Field(default=None, max_length=20)
    phone: str | None = Field(default=None, pattern=PHONE_PATTERN)
    address: str | None = None
    national_id: str | None = Field(default=None, max_length=50)
    notes: str | None = None
    project_ids: list[int] = Field(default_factory=list)


class BeneficiaryUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    category: BeneficiaryCategory | None = None
    age: int | None = Field(default=None, ge=0, le=120)
    gender: str | None = Field(default=None, max_length=20)
    phone: str | None = Field(default=None, pattern=PHONE_PATTERN)
    address: str | None = None
    national_id: str | None = Field(default=None, max_length=50)
    notes: str | None = None


class BeneficiaryOut(ORMModel):
    id: int
    full_name: str
    category: BeneficiaryCategory
    age: int | None
    gender: str | None
    # Sensitive fields: null (or masked) unless the caller has beneficiaries:sensitive
    phone: str | None
    address: str | None
    national_id: str | None
    notes: str | None
    project_ids: list[int] = []
    created_at: datetime
