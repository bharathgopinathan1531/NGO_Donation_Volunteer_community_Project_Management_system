from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Budget(Base, TimestampMixin):
    """A budget belongs to exactly one campaign OR one project (one budget each)."""

    __tablename__ = "budgets"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="amount_non_negative"),
        CheckConstraint(
            "(campaign_id IS NOT NULL AND project_id IS NULL) OR (campaign_id IS NULL AND project_id IS NOT NULL)",
            name="exactly_one_scope",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int | None] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), unique=True, nullable=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), unique=True, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
