from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_permissions
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Message, Page
from app.schemas.milestone import MilestoneCreate, MilestoneOut, MilestoneUpdate
from app.services.milestone_service import MilestoneService
from app.utils.enums import MilestoneStatus
from app.utils.pagination import PaginationParams, build_page, pagination_params
from app.utils.sorting import SortParams, sort_params

router = APIRouter(prefix="/milestones", tags=["Milestones"])
writer = require_permissions(Permission.MILESTONES_WRITE)


@router.post("", response_model=MilestoneOut, status_code=status.HTTP_201_CREATED)
def create_milestone(payload: MilestoneCreate, actor: User = Depends(writer), db: Session = Depends(get_db)):
    return MilestoneService.serialize(MilestoneService(db).create(actor, payload))


@router.get("", response_model=Page[MilestoneOut], summary="List milestones (overdue_only=true finds late ones)")
def list_milestones(
    project_id: int | None = None, status: MilestoneStatus | None = None, overdue_only: bool = False,
    params: PaginationParams = Depends(pagination_params), sort: SortParams = Depends(sort_params),
    actor: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    items, total = MilestoneService(db).list_milestones(actor, params, sort, project_id=project_id, status=status, overdue_only=overdue_only)
    return build_page([MilestoneService.serialize(i) for i in items], total, params)


@router.get("/{milestone_id}", response_model=MilestoneOut)
def get_milestone(milestone_id: int, actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return MilestoneService.serialize(MilestoneService(db).get_for_actor(actor, milestone_id))


@router.patch("/{milestone_id}", response_model=MilestoneOut)
def update_milestone(milestone_id: int, payload: MilestoneUpdate, actor: User = Depends(writer), db: Session = Depends(get_db)):
    return MilestoneService.serialize(MilestoneService(db).update(actor, milestone_id, payload))


@router.delete("/{milestone_id}", response_model=Message)
def delete_milestone(milestone_id: int, actor: User = Depends(writer), db: Session = Depends(get_db)):
    MilestoneService(db).delete(actor, milestone_id)
    return Message(message="Milestone deleted")
