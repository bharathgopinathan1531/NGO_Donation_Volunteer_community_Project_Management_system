from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_permissions
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Message, Page
from app.schemas.task import TaskCreate, TaskOut, TaskUpdate
from app.services.task_service import TaskService, serialize
from app.utils.enums import TaskPriority, TaskStatus
from app.utils.pagination import PaginationParams, build_page, pagination_params
from app.utils.sorting import SortParams, sort_params

router = APIRouter(prefix="/tasks", tags=["Tasks"])
writer = require_permissions(Permission.TASKS_WRITE)


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED, summary="Create and assign a task")
def create_task(payload: TaskCreate, actor: User = Depends(writer), db: Session = Depends(get_db)):
    return serialize(TaskService(db).create(actor, payload))


def _list(db, actor, params, sort, **kw):
    items, total = TaskService(db).list_tasks(actor, params, sort, **kw)
    return build_page([serialize(i) for i in items], total, params)


@router.get("", response_model=Page[TaskOut], summary="List tasks (staff: all; others: their own)")
def list_tasks(
    milestone_id: int | None = None, project_id: int | None = None, assignee_id: int | None = None,
    status: TaskStatus | None = None, priority: TaskPriority | None = None, overdue_only: bool = False,
    params: PaginationParams = Depends(pagination_params), sort: SortParams = Depends(sort_params),
    actor: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    return _list(db, actor, params, sort, milestone_id=milestone_id, project_id=project_id, assignee_id=assignee_id,
                 status=status, priority=priority, overdue_only=overdue_only)


@router.get("/overdue", response_model=Page[TaskOut], summary="Overdue tasks")
def overdue_tasks(
    project_id: int | None = None, assignee_id: int | None = None,
    params: PaginationParams = Depends(pagination_params), sort: SortParams = Depends(sort_params),
    actor: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    return _list(db, actor, params, sort, milestone_id=None, project_id=project_id, assignee_id=assignee_id,
                 status=None, priority=None, overdue_only=True)


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return serialize(TaskService(db).get_for_actor(actor, task_id))


@router.patch("/{task_id}", response_model=TaskOut, summary="Update task status / progress (assignees may update their own)")
def update_task(task_id: int, payload: TaskUpdate, actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return serialize(TaskService(db).update(actor, task_id, payload))


@router.delete("/{task_id}", response_model=Message)
def delete_task(task_id: int, actor: User = Depends(writer), db: Session = Depends(get_db)):
    TaskService(db).delete(actor, task_id)
    return Message(message="Task deleted")
