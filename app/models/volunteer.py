from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, enum_type
from app.utils.enums import VolunteerStatus


class Volunteer(Base, TimestampMixin):
    __tablename__ = "volunteers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True)
    full_name: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills: Mapped[str | None] = mapped_column(Text, nullable=True)  # comma separated
    experience: Mapped[str | None] = mapped_column(Text, nullable=True)
    availability: Mapped[str | None] = mapped_column(String(255), nullable=True)  # e.g. "weekends", "weekday evenings"
    status: Mapped[VolunteerStatus] = mapped_column(enum_type(VolunteerStatus), default=VolunteerStatus.ACTIVE, nullable=False, index=True)
    emergency_contact_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    emergency_contact_relation: Mapped[str | None] = mapped_column(String(50), nullable=True)
