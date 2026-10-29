from datetime import date

from sqlalchemy import select

from app.models.milestone import Milestone
from app.models.task import Task
from app.repositories import BaseRepository
from app.utils.enums import TaskPriority, TaskStatus
from app.utils.filtering import apply_equals
from app.utils.pagination import PaginationParams, paginate
from app.utils.sorting import SortParams, apply_sorting


class TaskRepository(BaseRepository[Task]):
    model = Task

    def for_milestone(self, milestone_id: int) -> list[Task]:
        return list(self.db.scalars(select(Task).where(Task.milestone_id == milestone_id)).all())

    def list_tasks(
        self, params: PaginationParams, sort: SortParams, *, milestone_id: int | None = None, project_id: int | None = None,
        assignee_id: int | None = None, status: TaskStatus | None = None, priority: TaskPriority | None = None,
        overdue_only: bool = False, today: date | None = None,
    ):
        stmt = apply_equals(select(Task), Task, milestone_id=milestone_id, assignee_id=assignee_id, status=status, priority=priority)
        if project_id is not None:
            stmt = stmt.join(Milestone, Milestone.id == Task.milestone_id).where(Milestone.project_id == project_id)
        if overdue_only and today:
            stmt = stmt.where(Task.deadline < today, Task.status != TaskStatus.COMPLETED)
        stmt = apply_sorting(stmt, Task, sort, {"id", "deadline", "priority", "status", "progress", "created_at"}, default="deadline")
        return paginate(self.db, stmt, params)
