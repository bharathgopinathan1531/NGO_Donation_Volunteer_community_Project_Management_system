from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_permissions
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page
from app.schemas.donation import DonationOut
from app.schemas.donor import DonorCreate, DonorOut, DonorUpdate
from app.services.donor_service import DonorService
from app.utils.enums import DonationMethod, DonationStatus, DonorStatus, DonorType
from app.utils.pagination import PaginationParams, build_page, pagination_params
from app.utils.sorting import SortParams, sort_params

router = APIRouter(prefix="/donors", tags=["Donors"])


@router.post("", response_model=DonorOut, status_code=status.HTTP_201_CREATED, summary="Create a donor profile")
def create_donor(payload: DonorCreate, actor: User = Depends(require_permissions(Permission.DONORS_WRITE)), db: Session = Depends(get_db)):
    return DonorService(db).create(actor, payload)


@router.get("", response_model=Page[DonorOut], summary="Search and filter donors")
def list_donors(
    search: str | None = Query(None, description="Matches name, email, phone, contact person"),
    donor_type: DonorType | None = None, status: DonorStatus | None = None, city: str | None = None, country: str | None = None,
    params: PaginationParams = Depends(pagination_params), sort: SortParams = Depends(sort_params),
    _: User = Depends(require_permissions(Permission.DONORS_READ)), db: Session = Depends(get_db),
):
    items, total = DonorService(db).list_donors(params, sort, search=search, donor_type=donor_type, status=status, city=city, country=country)
    return build_page([DonorOut.model_validate(i) for i in items], total, params)


@router.get("/me", response_model=DonorOut, summary="The donor profile linked to my account")
def my_profile(actor: User = Depends(require_permissions(Permission.DONORS_READ_OWN)), db: Session = Depends(get_db)):
    return DonorService(db).me(actor)


@router.get("/{donor_id}", response_model=DonorOut)
def get_donor(donor_id: int, actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return DonorService(db).get_for_actor(actor, donor_id)


@router.patch("/{donor_id}", response_model=DonorOut, summary="Update a donor profile")
def update_donor(donor_id: int, payload: DonorUpdate, actor: User = Depends(require_permissions(Permission.DONORS_WRITE)), db: Session = Depends(get_db)):
    return DonorService(db).update(actor, donor_id, payload)


@router.get("/{donor_id}/donations", response_model=Page[DonationOut], summary="Donation history of a donor")
def donor_donations(
    donor_id: int, status: DonationStatus | None = None, method: DonationMethod | None = None,
    date_from: date | None = None, date_to: date | None = None,
    params: PaginationParams = Depends(pagination_params), sort: SortParams = Depends(sort_params),
    actor: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    items, total = DonorService(db).donation_history(
        actor, donor_id, params, sort, campaign_id=None, status=status, method=method, search=None, date_from=date_from, date_to=date_to
    )
    return build_page([DonationOut.model_validate(i) for i in items], total, params)
