from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class BeneficiaryAssistance(Base, TimestampMixin):
    __tablename__ = "beneficiary_assistance"
    __table_args__ = (CheckConstraint("quantity >= 0", name="quantity_non_negative"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    beneficiary_id: Mapped[int] = mapped_column(ForeignKey("beneficiaries.id", ondelete="RESTRICT"), nullable=False, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False, index=True)
    resource_id: Mapped[int | None] = mapped_column(ForeignKey("resources.id", ondelete="RESTRICT"), nullable=True, index=True)
    assistance_type: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # units of the resource distributed
    distribution_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
