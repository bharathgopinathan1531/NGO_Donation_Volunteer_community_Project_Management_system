from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, enum_type
from app.utils.enums import AssignmentStatus


class VolunteerAssignment(Base, TimestampMixin):
    __tablename__ = "volunteer_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    volunteer_id: Mapped[int] = mapped_column(ForeignKey("volunteers.id", ondelete="RESTRICT"), nullable=False, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False, index=True)
    responsibility: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[AssignmentStatus] = mapped_column(enum_type(AssignmentStatus), default=AssignmentStatus.ASSIGNED, nullable=False, index=True)
    hours_completed: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0.00"), nullable=False)
    assigned_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    volunteer = relationship("Volunteer")
    project = relationship("Project")
