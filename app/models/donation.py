from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, enum_type
from app.utils.enums import DonationMethod, DonationStatus


class Donation(Base, TimestampMixin):
    __tablename__ = "donations"
    __table_args__ = (CheckConstraint("amount > 0", name="amount_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    donor_id: Mapped[int] = mapped_column(ForeignKey("donors.id", ondelete="RESTRICT"), nullable=False, index=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id", ondelete="RESTRICT"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    donation_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    method: Mapped[DonationMethod] = mapped_column(enum_type(DonationMethod), nullable=False)
    reference_number: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    status: Mapped[DonationStatus] = mapped_column(enum_type(DonationStatus), default=DonationStatus.PENDING, nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    donor = relationship("Donor", back_populates="donations")
    campaign = relationship("Campaign")
