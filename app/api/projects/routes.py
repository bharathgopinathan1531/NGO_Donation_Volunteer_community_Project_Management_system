from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_permissions
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page
from app.schemas.milestone import MilestoneOut
from app.schemas.project import ProjectCreate, ProjectDetail, ProjectOut, ProjectStatusChange, ProjectUpdate
from app.services.milestone_service import MilestoneService
from app.services.project_service import ProjectService
from app.utils.enums import ProjectStatus
from app.utils.pagination import PaginationParams, build_page, pagination_params
from app.utils.sorting import SortParams, sort_params

router = APIRouter(prefix="/projects", tags=["Community Projects"])
writer = require_permissions(Permission.PROJECTS_WRITE)


@router.post("", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED, summary="Create a community project (starts in planning)")
def create_project(payload: ProjectCreate, actor: User = Depends(writer), db: Session = Depends(get_db)):
    svc = ProjectService(db)
    return svc.serialize(svc.create(actor, payload))


@router.get("", response_model=Page[ProjectOut], summary="List projects (volunteers see only projects they are assigned to)")
def list_projects(
    search: str | None = None, status: ProjectStatus | None = None, manager_id: int | None = None, campaign_id: int | None = None,
    location: str | None = None, date_from: date | None = Query(None, description="Start on/after"), date_to: date | None = Query(None, description="Start on/before"),
    params: PaginationParams = Depends(pagination_params), sort: SortParams = Depends(sort_params),
    actor: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    items, total = ProjectService(db).list_projects(
        actor, params, sort, search=search, status=status, manager_id=manager_id, campaign_id=campaign_id, location=location,
        date_from=date_from, date_to=date_to,
    )
    return build_page([ProjectOut.model_validate(i) for i in items], total, params)


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(project_id: int, actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    svc = ProjectService(db)
    return svc.serialize(svc.get_for_actor(actor, project_id))


@router.patch("/{project_id}", response_model=ProjectDetail)
def update_project(project_id: int, payload: ProjectUpdate, actor: User = Depends(writer), db: Session = Depends(get_db)):
    svc = ProjectService(db)
    return svc.serialize(svc.update(actor, project_id, payload))


@router.post("/{project_id}/status", response_model=ProjectDetail, summary="Change status (activation requires approval)")
def change_status(project_id: int, payload: ProjectStatusChange, actor: User = Depends(writer), db: Session = Depends(get_db)):
    svc = ProjectService(db)
    return svc.serialize(svc.change_status(actor, project_id, payload.status))


@router.get("/{project_id}/milestones", response_model=list[MilestoneOut], summary="Milestone tracking for a project")
def project_milestones(project_id: int, actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ProjectService(db).get_for_actor(actor, project_id)
    ms = sorted(MilestoneService(db).repo.for_project(project_id), key=lambda m: (m.due_date, m.id))
    return [MilestoneService.serialize(m) for m in ms]
