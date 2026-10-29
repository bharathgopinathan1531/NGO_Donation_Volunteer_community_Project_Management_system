from datetime import date

from sqlalchemy import select

from app.models.milestone import Milestone
from app.models.project import Project
from app.repositories import BaseRepository
from app.utils.enums import MilestoneStatus, ProjectStatus
from app.utils.filtering import apply_equals
from app.utils.pagination import PaginationParams, paginate
from app.utils.sorting import SortParams, apply_sorting


class MilestoneRepository(BaseRepository[Milestone]):
    model = Milestone

    def list_milestones(
        self, params: PaginationParams, sort: SortParams, *, project_id: int | None = None, status: MilestoneStatus | None = None,
        overdue_only: bool = False, today: date | None = None,
    ):
        stmt = apply_equals(select(Milestone), Milestone, project_id=project_id, status=status)
        if overdue_only and today:
            stmt = stmt.where(Milestone.due_date < today, Milestone.status != MilestoneStatus.COMPLETED)
        stmt = apply_sorting(stmt, Milestone, sort, {"id", "due_date", "status", "created_at", "title"}, default="due_date")
        return paginate(self.db, stmt, params)

    def overdue(self, today: date) -> list[Milestone]:
        """Overdue milestones of projects that are still running."""
        stmt = (
            select(Milestone)
            .join(Project, Project.id == Milestone.project_id)
            .where(
                Milestone.due_date < today, Milestone.status != MilestoneStatus.COMPLETED,
                Project.status.notin_([ProjectStatus.CANCELLED, ProjectStatus.COMPLETED]),
            )
        )
        return list(self.db.scalars(stmt).all())

    def for_project(self, project_id: int) -> list[Milestone]:
        return list(self.db.scalars(select(Milestone).where(Milestone.project_id == project_id)).all())
