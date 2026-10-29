from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, enum_type
from app.utils.date_utils import utcnow
from app.utils.enums import ApprovalAction


class ProjectApproval(Base):
    """Append-only approval history. The latest row decides the current approval state."""

    __tablename__ = "project_approvals"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    action: Mapped[ApprovalAction] = mapped_column(enum_type(ApprovalAction), nullable=False)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
