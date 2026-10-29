from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_permissions
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page
from app.schemas.volunteer import VolunteerCreate, VolunteerOut, VolunteerUpdate
from app.services.volunteer_service import VolunteerService, to_out
from app.utils.enums import VolunteerStatus
from app.utils.pagination import PaginationParams, build_page, pagination_params
from app.utils.sorting import SortParams, sort_params

router = APIRouter(prefix="/volunteers", tags=["Volunteers"])


@router.post("", response_model=VolunteerOut, status_code=status.HTTP_201_CREATED, summary="Register a volunteer (staff)")
def register_volunteer(payload: VolunteerCreate, actor: User = Depends(require_permissions(Permission.VOLUNTEERS_WRITE)), db: Session = Depends(get_db)):
    return to_out(VolunteerService(db).create(actor, payload))


@router.post("/me", response_model=VolunteerOut, status_code=status.HTTP_201_CREATED, summary="Create my own volunteer profile")
def register_me(payload: VolunteerCreate, actor: User = Depends(require_permissions(Permission.VOLUNTEERS_REGISTER_SELF)), db: Session = Depends(get_db)):
    return to_out(VolunteerService(db).register_self(actor, payload))


@router.get("/me", response_model=VolunteerOut, summary="My volunteer profile")
def my_profile(actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return to_out(VolunteerService(db).me(actor))


@router.get("", response_model=Page[VolunteerOut], summary="Search and filter volunteers")
def list_volunteers(
    search: str | None = Query(None, description="Name, email or phone"), status: VolunteerStatus | None = None,
    skill: str | None = Query(None, description="Contains skill"), availability: str | None = None,
    params: PaginationParams = Depends(pagination_params), sort: SortParams = Depends(sort_params),
    _: User = Depends(require_permissions(Permission.VOLUNTEERS_READ)), db: Session = Depends(get_db),
):
    items, total = VolunteerService(db).list_volunteers(params, sort, search=search, status=status, skill=skill, availability=availability)
    return build_page([to_out(i) for i in items], total, params)


@router.get("/{volunteer_id}", response_model=VolunteerOut)
def get_volunteer(volunteer_id: int, actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return to_out(VolunteerService(db).get_for_actor(actor, volunteer_id))


@router.patch("/{volunteer_id}", response_model=VolunteerOut, summary="Update a volunteer (own profile or staff)")
def update_volunteer(volunteer_id: int, payload: VolunteerUpdate, actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return to_out(VolunteerService(db).update(actor, volunteer_id, payload))
