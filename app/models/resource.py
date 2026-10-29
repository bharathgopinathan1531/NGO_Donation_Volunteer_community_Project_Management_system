from decimal import Decimal

from sqlalchemy import CheckConstraint, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, enum_type
from app.utils.enums import ResourceCategory


class Resource(Base, TimestampMixin):
    __tablename__ = "resources"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="quantity_non_negative"),  # DB-level guard against negative inventory
        CheckConstraint("low_stock_threshold >= 0", name="threshold_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    category: Mapped[ResourceCategory] = mapped_column(enum_type(ResourceCategory), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str] = mapped_column(String(30), default="unit", nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
