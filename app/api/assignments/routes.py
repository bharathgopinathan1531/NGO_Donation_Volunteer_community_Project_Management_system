from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_permissions
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.assignment import AssignmentCreate, AssignmentOut, AssignmentStatusChange, AssignmentUpdate
from app.schemas.common import Page
from app.services.assignment_service import AssignmentService
from app.utils.enums import AssignmentStatus
from app.utils.pagination import PaginationParams, build_page, pagination_params
from app.utils.sorting import SortParams, sort_params

router = APIRouter(prefix="/assignments", tags=["Volunteer Assignments"])
writer = require_permissions(Permission.ASSIGNMENTS_WRITE)


@router.post("", response_model=AssignmentOut, status_code=status.HTTP_201_CREATED, summary="Assign a volunteer to a project (rejects overlapping assignments)")
def create_assignment(payload: AssignmentCreate, actor: User = Depends(writer), db: Session = Depends(get_db)):
    return AssignmentService(db).create(actor, payload)


@router.get("", response_model=Page[AssignmentOut], summary="Assignment history (volunteers see only their own)")
def list_assignments(
    volunteer_id: int | None = None, project_id: int | None = None, status: AssignmentStatus | None = None,
    date_from: date | None = None, date_to: date | None = None,
    params: PaginationParams = Depends(pagination_params), sort: SortParams = Depends(sort_params),
    actor: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    items, total = AssignmentService(db).list_assignments(
        actor, params, sort, volunteer_id=volunteer_id, project_id=project_id, status=status, date_from=date_from, date_to=date_to
    )
    return build_page([AssignmentOut.model_validate(i) for i in items], total, params)


@router.get("/{assignment_id}", response_model=AssignmentOut)
def get_assignment(assignment_id: int, actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AssignmentService(db).get_for_actor(actor, assignment_id)


@router.patch("/{assignment_id}", response_model=AssignmentOut)
def update_assignment(assignment_id: int, payload: AssignmentUpdate, actor: User = Depends(writer), db: Session = Depends(get_db)):
    return AssignmentService(db).update(actor, assignment_id, payload)


@router.post("/{assignment_id}/status", response_model=AssignmentOut, summary="Activate, complete or cancel an assignment")
def change_status(assignment_id: int, payload: AssignmentStatusChange, actor: User = Depends(writer), db: Session = Depends(get_db)):
    return AssignmentService(db).change_status(actor, assignment_id, payload.status)
