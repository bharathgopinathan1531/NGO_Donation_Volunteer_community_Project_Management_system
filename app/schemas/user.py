from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.security import validate_password_strength
from app.schemas.common import ORMModel
from app.utils.enums import Role


class UserOut(ORMModel):
    id: int
    email: EmailStr
    full_name: str
    role: Role
    is_active: bool
    created_at: datetime


class UserCreate(BaseModel):
    """Admin-created account (any role)."""

    email: EmailStr
    full_name: str = Field(min_length=2, max_length=150)
    password: str = Field(min_length=8, max_length=128)
    role: Role

    @field_validator("password")
    @classmethod
    def _strong(cls, v: str) -> str:
        return validate_password_strength(v)


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    role: Role | None = None
