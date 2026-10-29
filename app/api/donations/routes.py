from datetime import date

from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_permissions
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page
from app.schemas.donation import DonationCreate, DonationOut, DonationUpdate
from app.schemas.receipt import ReceiptOut
from app.services.donation_service import DonationService
from app.services.receipt_service import ReceiptService
from app.utils.enums import DonationMethod, DonationStatus
from app.utils.pagination import PaginationParams, build_page, pagination_params
from app.utils.sorting import SortParams, sort_params

router = APIRouter(prefix="/donations", tags=["Donations"])
writer = require_permissions(Permission.DONATIONS_WRITE)


@router.post("", response_model=DonationOut, status_code=status.HTTP_201_CREATED, summary="Record a donation")
def create_donation(payload: DonationCreate, actor: User = Depends(writer), db: Session = Depends(get_db)):
    return DonationService(db).create(actor, payload)


@router.get("", response_model=Page[DonationOut], summary="Donation history with filters")
def list_donations(
    donor_id: int | None = None, campaign_id: int | None = None, status: DonationStatus | None = None,
    method: DonationMethod | None = None, search: str | None = Query(None, description="Reference number / notes"),
    date_from: date | None = None, date_to: date | None = None,
    params: PaginationParams = Depends(pagination_params), sort: SortParams = Depends(sort_params),
    actor: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    items, total = DonationService(db).list_donations(
        actor, params, sort, donor_id=donor_id, campaign_id=campaign_id, status=status, method=method, search=search,
        date_from=date_from, date_to=date_to,
    )
    return build_page([DonationOut.model_validate(i) for i in items], total, params)


@router.get("/{donation_id}", response_model=DonationOut)
def get_donation(donation_id: int, actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return DonationService(db).get_for_actor(actor, donation_id)


@router.patch("/{donation_id}", response_model=DonationOut, summary="Edit a donation (financial fields only while pending)")
def update_donation(donation_id: int, payload: DonationUpdate, actor: User = Depends(writer), db: Session = Depends(get_db)):
    return DonationService(db).update(actor, donation_id, payload)


@router.get("/{donation_id}/receipt", response_model=ReceiptOut, summary="Receipt of a donation")
def donation_receipt(donation_id: int, actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ReceiptService(db).for_donation(actor, donation_id)


def _status_route(path: str, target: DonationStatus, summary: str):
    def endpoint(donation_id: int, reason: str | None = Body(None, embed=True, max_length=255), actor: User = Depends(writer), db: Session = Depends(get_db)):
        return DonationService(db).change_status(actor, donation_id, target, reason)

    router.add_api_route(f"/{{donation_id}}/{path}", endpoint, methods=["POST"], response_model=DonationOut, summary=summary)


_status_route("confirm", DonationStatus.CONFIRMED, "Confirm a pending donation (adds it to the campaign total)")
_status_route("cancel", DonationStatus.CANCELLED, "Cancel a pending donation")
_status_route("reverse", DonationStatus.REVERSED, "Reverse a confirmed donation (deducts from campaign total, voids receipt)")
_status_route("refund", DonationStatus.REFUNDED, "Refund a confirmed donation (deducts from campaign total, voids receipt)")
