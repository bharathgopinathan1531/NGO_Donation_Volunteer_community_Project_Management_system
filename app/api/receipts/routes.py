from fastapi import APIRouter, Depends, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_permissions
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Page
from app.schemas.receipt import ReceiptCreate, ReceiptOut
from app.services.receipt_service import ReceiptService
from app.utils.enums import ReceiptStatus
from app.utils.pagination import PaginationParams, build_page, pagination_params
from app.utils.sorting import SortParams, sort_params

router = APIRouter(prefix="/receipts", tags=["Receipts"])


@router.post("", response_model=ReceiptOut, status_code=status.HTTP_201_CREATED, summary="Generate a receipt for a confirmed donation")
def issue_receipt(payload: ReceiptCreate, actor: User = Depends(require_permissions(Permission.RECEIPTS_WRITE)), db: Session = Depends(get_db)):
    return ReceiptService(db).issue(actor, payload.donation_id)


@router.get("", response_model=Page[ReceiptOut])
def list_receipts(
    donor_id: int | None = None, status: ReceiptStatus | None = None,
    params: PaginationParams = Depends(pagination_params), sort: SortParams = Depends(sort_params),
    actor: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    items, total = ReceiptService(db).list_receipts(actor, params, sort, donor_id=donor_id, status=status)
    return build_page([ReceiptOut.model_validate(i) for i in items], total, params)


@router.get("/donor/{donor_id}", response_model=Page[ReceiptOut], summary="Receipts of a donor")
def receipts_by_donor(
    donor_id: int, status: ReceiptStatus | None = None,
    params: PaginationParams = Depends(pagination_params), sort: SortParams = Depends(sort_params),
    actor: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    items, total = ReceiptService(db).list_receipts(actor, params, sort, donor_id=donor_id, status=status)
    return build_page([ReceiptOut.model_validate(i) for i in items], total, params)


@router.get("/by-number/{receipt_number}", response_model=ReceiptOut)
def get_by_number(receipt_number: str, actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ReceiptService(db).get_by_number(actor, receipt_number)


@router.get("/{receipt_id}", response_model=ReceiptOut)
def get_receipt(receipt_id: int, actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ReceiptService(db).get(actor, receipt_id)


@router.get("/{receipt_id}/pdf", summary="Download the receipt as a PDF", response_class=Response)
def receipt_pdf(receipt_id: int, actor: User = Depends(get_current_user), db: Session = Depends(get_db)):
    content, filename = ReceiptService(db).pdf(actor, receipt_id)
    return Response(content, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
