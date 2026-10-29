from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.utils.date_utils import utcnow


class ImpactUpdate(Base):
    """Point-in-time impact snapshot submitted by a project manager (append-only history)."""

    __tablename__ = "impact_updates"
    __table_args__ = (
        CheckConstraint(
            "beneficiaries_served >= 0 AND resources_distributed >= 0 AND milestones_achieved >= 0 "
            "AND volunteer_hours >= 0 AND funds_utilized >= 0",
            name="metrics_non_negative",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    beneficiaries_served: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    volunteer_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    resources_distributed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    funds_utilized: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)
    milestones_achieved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    project_completed: Mapped[bool] = mapped_column(default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False, index=True)
