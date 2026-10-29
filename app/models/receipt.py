from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, enum_type
from app.utils.date_utils import utcnow
from app.utils.enums import ReceiptStatus


class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(primary_key=True)
    receipt_number: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    # unique => at most one receipt per donation (duplicate prevention at DB level)
    donation_id: Mapped[int] = mapped_column(ForeignKey("donations.id", ondelete="RESTRICT"), unique=True, nullable=False)
    donor_id: Mapped[int] = mapped_column(ForeignKey("donors.id", ondelete="RESTRICT"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    status: Mapped[ReceiptStatus] = mapped_column(enum_type(ReceiptStatus), default=ReceiptStatus.ISSUED, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    issued_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    void_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meta: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)  # snapshot: donor/campaign names, method, reference

    donation = relationship("Donation")
    donor = relationship("Donor")
