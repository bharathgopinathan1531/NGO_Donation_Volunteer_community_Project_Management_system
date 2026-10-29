from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ORMModel
from app.utils.enums import AttendanceStatus


class AttendanceCreate(BaseModel):
    assignment_id: int
    attendance_date: date
    status: AttendanceStatus = AttendanceStatus.PRESENT
    hours: Decimal = Field(default=Decimal("0"), ge=0, le=24, max_digits=5, decimal_places=2)
    notes: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def _hours_vs_status(self):
        if self.status == AttendanceStatus.PRESENT and self.hours <= 0:
            raise ValueError("A 'present' record needs hours > 0")
        if self.status != AttendanceStatus.PRESENT and self.hours != 0:
            raise ValueError("Hours must be 0 unless status is 'present'")
        return self


class AttendanceUpdate(BaseModel):
    status: AttendanceStatus | None = None
    hours: Decimal | None = Field(default=None, ge=0, le=24, max_digits=5, decimal_places=2)
    notes: str | None = Field(default=None, max_length=255)


class AttendanceOut(ORMModel):
    id: int
    assignment_id: int
    attendance_date: date
    status: AttendanceStatus
    hours: Decimal
    notes: str | None
    recorded_by: int | None
    created_at: datetime
