from sqlalchemy import Column, ForeignKey, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, enum_type
from app.utils.enums import BeneficiaryCategory

beneficiary_projects = Table(
    "beneficiary_projects",
    Base.metadata,
    Column("beneficiary_id", ForeignKey("beneficiaries.id", ondelete="CASCADE"), primary_key=True),
    Column("project_id", ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
)


class Beneficiary(Base, TimestampMixin):
    __tablename__ = "beneficiaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    category: Mapped[BeneficiaryCategory] = mapped_column(enum_type(BeneficiaryCategory), nullable=False, index=True)
    age: Mapped[int | None] = mapped_column(nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # --- sensitive fields: only returned to roles with beneficiaries:sensitive ---
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    national_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    registered_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    projects = relationship("Project", secondary=beneficiary_projects)
