from datetime import date

from sqlalchemy.orm import Session

from app.core.constants import PROJECT_CLOSED_STATUSES
from app.core.exceptions import BusinessRuleError, ForbiddenError, NotFoundError
from app.core.permissions import Permission, has_permission
from app.db.session import transaction
from app.models.task import Task
from app.models.user import User
from app.repositories.milestone_repository import MilestoneRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.schemas.task import TaskCreate, TaskOut, TaskUpdate
from app.services.audit_service import AuditService, diff, snapshot
from app.services.milestone_service import recompute_status
from app.services.project_service import ProjectService
from app.utils.date_utils import today
from app.utils.enums import TaskPriority, TaskStatus
from app.utils.pagination import PaginationParams
from app.utils.sorting import SortParams

AUDIT_FIELDS = ["title", "assignee_id", "priority", "status", "progress", "deadline"]
STAFF_ONLY_FIELDS = {"title", "description", "assignee_id", "priority", "deadline"}


def serialize(t: Task) -> TaskOut:
    out = TaskOut.model_validate(t)
    out.is_overdue = t.deadline < today() and t.status != TaskStatus.COMPLETED
    return out


class TaskService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = TaskRepository(db)
        self.milestones = MilestoneRepository(db)
        self.projects = ProjectRepository(db)
        self.audit = AuditService(db)

    def _validate_assignee(self, assignee_id: int | None) -> None:
        if assignee_id is None:
            return
        u = UserRepository(self.db).get(assignee_id)
        if not u or not u.is_active:
            raise NotFoundError("Assignee not found or inactive")

    def get_for_actor(self, actor: User, task_id: int) -> Task:
        t = self.repo.get(task_id)
        if not t:
            raise NotFoundError("Task not found")
        m = self.milestones.get(t.milestone_id)
        if has_permission(actor.role, Permission.TASKS_WRITE) or t.assignee_id == actor.id:
            return t
        ProjectService(self.db).get_for_actor(actor, m.project_id)
        return t

    def create(self, actor: User, data: TaskCreate) -> Task:
        with transaction(self.db):
            m = self.milestones.get(data.milestone_id)
            if not m:
                raise NotFoundError("Milestone not found")
            p = self.projects.get(m.project_id)
            if p.status in PROJECT_CLOSED_STATUSES:
                raise BusinessRuleError(f"Project is {p.status.value}; tasks cannot be added")
            if data.deadline < p.start_date or data.deadline > p.end_date:
                raise BusinessRuleError(f"Task deadline must fall within the project period ({p.start_date} to {p.end_date})")
            self._validate_assignee(data.assignee_id)
            t = self.repo.add(Task(**data.model_dump()))
            self.db.refresh(m)
            recompute_status(m)
            self.audit.log(actor, "task.created", "task", t.id, snapshot(t, AUDIT_FIELDS))
        return t

    @staticmethod
    def _sync_status_progress(t: Task, changes: dict) -> None:
        status, progress = changes.get("status"), changes.get("progress")
        if status is not None and progress is None:
            if status == TaskStatus.COMPLETED:
                changes["progress"] = 100
            elif status == TaskStatus.TODO:
                changes["progress"] = 0
            elif t.progress == 100:  # re-opening a finished task
                changes["progress"] = 90
        elif progress is not None and status is None:
            if progress == 100:
                changes["status"] = TaskStatus.COMPLETED
            elif progress > 0 and t.status in (TaskStatus.TODO, TaskStatus.COMPLETED):
                changes["status"] = TaskStatus.IN_PROGRESS
            elif progress == 0 and t.status in (TaskStatus.COMPLETED, TaskStatus.IN_PROGRESS):
                changes["status"] = TaskStatus.TODO
        final_status = changes.get("status", t.status)
        final_progress = changes.get("progress", t.progress)
        if (final_status == TaskStatus.COMPLETED) != (final_progress == 100):
            raise BusinessRuleError("A task is completed exactly when its progress is 100%")
        if final_status == TaskStatus.TODO and final_progress != 0:
            raise BusinessRuleError("A 'todo' task must have 0% progress")

    def update(self, actor: User, task_id: int, data: TaskUpdate) -> Task:
        changes = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None or k in {"assignee_id", "description"}}
        with transaction(self.db):
            t = self.repo.get(task_id)
            if not t:
                raise NotFoundError("Task not found")
            full_access = has_permission(actor.role, Permission.TASKS_WRITE)
            if not full_access:
                if not (has_permission(actor.role, Permission.TASKS_UPDATE_OWN) and t.assignee_id == actor.id):
                    raise ForbiddenError("You can only update tasks assigned to you")
                if STAFF_ONLY_FIELDS & set(changes):
                    raise ForbiddenError("You can only update the status and progress of your own tasks")
            m = self.milestones.get(t.milestone_id)
            p = self.projects.get(m.project_id)
            if p.status in PROJECT_CLOSED_STATUSES:
                raise BusinessRuleError(f"Project is {p.status.value}; tasks cannot be changed")
            if "assignee_id" in changes:
                self._validate_assignee(changes["assignee_id"])
            if "deadline" in changes and not (p.start_date <= changes["deadline"] <= p.end_date):
                raise BusinessRuleError(f"Task deadline must fall within the project period ({p.start_date} to {p.end_date})")
            self._sync_status_progress(t, changes)
            before = snapshot(t, AUDIT_FIELDS)
            for k, v in changes.items():
                setattr(t, k, v)
            self.db.flush()
            self.db.refresh(m)
            recompute_status(m)
            self.audit.log(actor, "task.updated", "task", t.id, diff(before, snapshot(t, AUDIT_FIELDS)))
        return t

    def delete(self, actor: User, task_id: int) -> None:
        with transaction(self.db):
            t = self.repo.get(task_id)
            if not t:
                raise NotFoundError("Task not found")
            m = self.milestones.get(t.milestone_id)
            self.repo.delete(t)
            self.db.refresh(m)
            recompute_status(m)
            self.audit.log(actor, "task.deleted", "task", task_id, {"title": t.title})

    def list_tasks(
        self, actor: User, params: PaginationParams, sort: SortParams, *, milestone_id: int | None, project_id: int | None,
        assignee_id: int | None, status: TaskStatus | None, priority: TaskPriority | None, overdue_only: bool,
    ):
        if not has_permission(actor.role, Permission.TASKS_WRITE):
            # volunteers (and anyone without task management rights) only see their own tasks
            if assignee_id is not None and assignee_id != actor.id:
                raise ForbiddenError("You can only list your own tasks")
            assignee_id = actor.id
        return self.repo.list_tasks(
            params, sort, milestone_id=milestone_id, project_id=project_id, assignee_id=assignee_id, status=status,
            priority=priority, overdue_only=overdue_only, today=today(),
        )
