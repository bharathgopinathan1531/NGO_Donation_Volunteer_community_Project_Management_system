from datetime import date, timedelta

from sqlalchemy import func, select

from app.models.project import Project
from app.models.project_approval import ProjectApproval
from app.models.volunteer_assignment import VolunteerAssignment
from app.repositories import BaseRepository
from app.utils.enums import ApprovalAction, AssignmentStatus, ProjectStatus
from app.utils.filtering import apply_date_range, apply_equals, apply_search
from app.utils.pagination import PaginationParams, paginate
from app.utils.sorting import SortParams, apply_sorting


class ProjectRepository(BaseRepository[Project]):
    model = Project

    def list_projects(
        self, params: PaginationParams, sort: SortParams, *, search: str | None, status: ProjectStatus | None,
        manager_id: int | None, campaign_id: int | None, location: str | None, date_from: date | None, date_to: date | None,
        only_project_ids: set[int] | None = None,
    ):
        stmt = apply_equals(select(Project), Project, status=status, manager_id=manager_id, campaign_id=campaign_id)
        stmt = apply_search(stmt, [Project.name, Project.description, Project.objectives], search)
        stmt = apply_search(stmt, [Project.location], location)
        stmt = apply_date_range(stmt, Project.start_date, date_from, date_to)
        if only_project_ids is not None:
            stmt = stmt.where(Project.id.in_(only_project_ids or {-1}))
        stmt = apply_sorting(stmt, Project, sort, {"id", "name", "start_date", "end_date", "budget", "status", "created_at"})
        return paginate(self.db, stmt, params)

    def ending_soon(self, today: date, days: int) -> list[Project]:
        stmt = select(Project).where(
            Project.status.in_([ProjectStatus.ACTIVE, ProjectStatus.APPROVED]),
            Project.end_date >= today, Project.end_date <= today + timedelta(days=days),
        )
        return list(self.db.scalars(stmt).all())

    def volunteer_has_access(self, volunteer_id: int, project_id: int) -> bool:
        stmt = select(VolunteerAssignment.id).where(
            VolunteerAssignment.volunteer_id == volunteer_id, VolunteerAssignment.project_id == project_id,
            VolunteerAssignment.status != AssignmentStatus.CANCELLED,
        ).limit(1)
        return self.db.scalar(stmt) is not None


class ApprovalRepository(BaseRepository[ProjectApproval]):
    model = ProjectApproval

    def latest(self, project_id: int) -> ProjectApproval | None:
        stmt = select(ProjectApproval).where(ProjectApproval.project_id == project_id).order_by(ProjectApproval.id.desc()).limit(1)
        return self.db.scalar(stmt)

    def history(self, project_id: int) -> list[ProjectApproval]:
        stmt = select(ProjectApproval).where(ProjectApproval.project_id == project_id).order_by(ProjectApproval.id)
        return list(self.db.scalars(stmt).all())

    def list_pending(self, params: PaginationParams):
        """Projects whose most recent approval record is a submission still awaiting a decision."""
        last = select(func.max(ProjectApproval.id)).group_by(ProjectApproval.project_id)
        stmt = select(ProjectApproval).where(ProjectApproval.id.in_(last), ProjectApproval.action == ApprovalAction.SUBMITTED).order_by(ProjectApproval.id)
        return paginate(self.db, stmt, params)
