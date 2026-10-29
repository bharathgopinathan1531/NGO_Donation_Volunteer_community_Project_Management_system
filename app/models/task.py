from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, enum_type
from app.utils.enums import TaskPriority, TaskStatus


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"
    __table_args__ = (CheckConstraint("progress >= 0 AND progress <= 100", name="progress_range"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    milestone_id: Mapped[int] = mapped_column(ForeignKey("milestones.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    priority: Mapped[TaskPriority] = mapped_column(enum_type(TaskPriority), default=TaskPriority.MEDIUM, nullable=False)
    status: Mapped[TaskStatus] = mapped_column(enum_type(TaskStatus), default=TaskStatus.TODO, nullable=False, index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deadline: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    milestone = relationship("Milestone", back_populates="tasks")
