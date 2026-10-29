from sqlalchemy import select

from app.models.receipt import Receipt
from app.repositories import BaseRepository
from app.utils.enums import ReceiptStatus
from app.utils.filtering import apply_equals
from app.utils.pagination import PaginationParams, paginate
from app.utils.sorting import SortParams, apply_sorting


class ReceiptRepository(BaseRepository[Receipt]):
    model = Receipt

    def get_by_donation(self, donation_id: int) -> Receipt | None:
        return self.db.scalar(select(Receipt).where(Receipt.donation_id == donation_id))

    def get_by_number(self, number: str) -> Receipt | None:
        return self.db.scalar(select(Receipt).where(Receipt.receipt_number == number))

    def list_receipts(self, params: PaginationParams, sort: SortParams, *, donor_id: int | None = None, status: ReceiptStatus | None = None):
        stmt = apply_equals(select(Receipt), Receipt, donor_id=donor_id, status=status)
        stmt = apply_sorting(stmt, Receipt, sort, {"id", "issued_at", "amount", "receipt_number"}, default="issued_at", default_order="desc")
        return paginate(self.db, stmt, params)
