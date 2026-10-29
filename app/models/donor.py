from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, enum_type
from app.utils.enums import DonorStatus, DonorType


class Donor(Base, TimestampMixin):
    __tablename__ = "donors"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    donor_type: Mapped[DonorType] = mapped_column(enum_type(DonorType), default=DonorType.INDIVIDUAL, nullable=False, index=True)
    status: Mapped[DonorStatus] = mapped_column(enum_type(DonorStatus), default=DonorStatus.ACTIVE, nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    contact_person: Mapped[str | None] = mapped_column(String(150), nullable=True)  # for organizations
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    donations = relationship("Donation", back_populates="donor", order_by="Donation.donation_date.desc()")
