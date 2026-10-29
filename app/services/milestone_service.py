from datetime import date

from sqlalchemy.orm import Session

from app.core.constants import MILESTONE_MANUAL_TRANSITIONS, PROJECT_CLOSED_STATUSES
from app.core.exceptions import BusinessRuleError, ForbiddenError, NotFoundError
from app.core.permissions import Permission, has_permission
from app.db.session import transaction
from app.models.milestone import Milestone
from app.models.user import User
from app.repositories.milestone_repository import MilestoneRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.milestone import MilestoneCreate, MilestoneOut, MilestoneUpdate
from app.services.audit_service import AuditService
from app.services.project_service import ProjectService
from app.utils.date_utils import today, utcnow
from app.utils.enums import MilestoneStatus, TaskStatus
from app.utils.pagination import PaginationParams
from app.utils.sorting import SortParams


def recompute_status(m: Milestone) -> None:
    """Milestone status is derived from its tasks whenever it has any."""
    tasks = list(m.tasks)
    if not tasks:
        return
    if all(t.status == TaskStatus.COMPLETED for t in tasks):
        new = MilestoneStatus.COMPLETED
    elif any(t.progress > 0 or t.status != TaskStatus.TODO for t in tasks):
        new = MilestoneStatus.IN_PROGRESS
    else:
        new = MilestoneStatus.PENDING
    if new != m.status:
        m.status = new
        m.completed_at = utcnow() if new == MilestoneStatus.COMPLETED else None


class MilestoneService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = MilestoneRepository(db)
        self.projects = ProjectRepository(db)
        self.audit = AuditService(db)

    @staticmethod
    def serialize(m: Milestone) -> MilestoneOut:
        out = MilestoneOut.model_validate(m)
        tasks = list(m.tasks)
        out.tasks_total = len(tasks)
        out.tasks_completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        if tasks:
            out.progress_pct = round(sum(t.progress for t in tasks) / len(tasks), 2)
        else:
            out.progress_pct = 100.0 if m.status == MilestoneStatus.COMPLETED else 0.0
        out.is_overdue = m.due_date < today() and m.status != MilestoneStatus.COMPLETED
        return out

    def get_for_actor(self, actor: User, milestone_id: int) -> Milestone:
        m = self.repo.get(milestone_id)
        if not m:
            raise NotFoundError("Milestone not found")
        ProjectService(self.db).get_for_actor(actor, m.project_id)  # enforces project visibility
        return m

    def create(self, actor: User, data: MilestoneCreate) -> Milestone:
        with transaction(self.db):
            p = self.projects.get(data.project_id)
            if not p:
                raise NotFoundError("Project not found")
            if p.status in PROJECT_CLOSED_STATUSES:
                raise BusinessRuleError(f"Project is {p.status.value}; milestones cannot be added")
            if data.due_date < p.start_date or data.due_date > p.end_date:
                raise BusinessRuleError(f"Milestone due date must fall within the project period ({p.start_date} to {p.end_date})")
            m = self.repo.add(Milestone(**data.model_dump()))
            self.audit.log(actor, "milestone.created", "milestone", m.id, {"project_id": p.id, "title": m.title, "due_date": m.due_date})
        return m

    def update(self, actor: User, milestone_id: int, data: MilestoneUpdate) -> Milestone:
        changes = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None or k == "description"}
        with transaction(self.db):
            m = self.repo.get(milestone_id)
            if not m:
                raise NotFoundError("Milestone not found")
            p = self.projects.get(m.project_id)
            if p.status in PROJECT_CLOSED_STATUSES:
                raise BusinessRuleError(f"Project is {p.status.value}; milestones cannot be changed")
            if "due_date" in changes and not (p.start_date <= changes["due_date"] <= p.end_date):
                raise BusinessRuleError(f"Milestone due date must fall within the project period ({p.start_date} to {p.end_date})")
            if "status" in changes:
                target = changes.pop("status")
                if list(m.tasks):
                    raise BusinessRuleError("This milestone has tasks; its status follows task progress")
                if target != m.status:
                    if target not in MILESTONE_MANUAL_TRANSITIONS.get(m.status, set()):
                        raise BusinessRuleError(f"Invalid milestone transition: '{m.status.value}' -> '{target.value}'")
                    m.status = target
                    m.completed_at = utcnow() if target == MilestoneStatus.COMPLETED else None
            old = {k: getattr(m, k) for k in changes}
            for k, v in changes.items():
                setattr(m, k, v)
            self.audit.log(actor, "milestone.updated", "milestone", m.id, {"changes": changes, "previous": old, "status": m.status})
        return m

    def delete(self, actor: User, milestone_id: int) -> None:
        with transaction(self.db):
            m = self.repo.get(milestone_id)
            if not m:
                raise NotFoundError("Milestone not found")
            if m.status == MilestoneStatus.COMPLETED or list(m.tasks):
                raise BusinessRuleError("Only empty, incomplete milestones can be deleted")
            self.repo.delete(m)
            self.audit.log(actor, "milestone.deleted", "milestone", milestone_id, {"title": m.title})

    def list_milestones(
        self, actor: User, params: PaginationParams, sort: SortParams, *, project_id: int | None, status: MilestoneStatus | None,
        overdue_only: bool,
    ):
        if project_id is not None:
            ProjectService(self.db).get_for_actor(actor, project_id)
        elif not has_permission(actor.role, Permission.PROJECTS_READ):
            raise ForbiddenError("Specify a project you are assigned to")
        return self.repo.list_milestones(params, sort, project_id=project_id, status=status, overdue_only=overdue_only, today=today())
