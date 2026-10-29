from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, enum_type
from app.utils.enums import CampaignCategory, CampaignStatus


class Campaign(Base, TimestampMixin):
    __tablename__ = "campaigns"
    __table_args__ = (
        CheckConstraint("goal_amount > 0", name="goal_positive"),
        CheckConstraint("raised_amount >= 0", name="raised_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[CampaignCategory] = mapped_column(enum_type(CampaignCategory), default=CampaignCategory.OTHER, nullable=False, index=True)
    status: Mapped[CampaignStatus] = mapped_column(enum_type(CampaignStatus), default=CampaignStatus.DRAFT, nullable=False, index=True)
    goal_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    raised_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    manager_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
