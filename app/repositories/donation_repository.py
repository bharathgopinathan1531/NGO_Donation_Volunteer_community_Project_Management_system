from datetime import date

from sqlalchemy import select

from app.models.donation import Donation
from app.repositories import BaseRepository
from app.utils.enums import DonationMethod, DonationStatus
from app.utils.filtering import apply_date_range, apply_equals, apply_search
from app.utils.pagination import PaginationParams, paginate
from app.utils.sorting import SortParams, apply_sorting


class DonationRepository(BaseRepository[Donation]):
    model = Donation

    def get_by_reference(self, reference: str) -> Donation | None:
        return self.db.scalar(select(Donation).where(Donation.reference_number == reference))

    def list_donations(
        self, params: PaginationParams, sort: SortParams, *, donor_id: int | None = None, campaign_id: int | None = None,
        status: DonationStatus | None = None, method: DonationMethod | None = None, search: str | None = None,
        date_from: date | None = None, date_to: date | None = None,
    ):
        stmt = apply_equals(select(Donation), Donation, donor_id=donor_id, campaign_id=campaign_id, status=status, method=method)
        stmt = apply_search(stmt, [Donation.reference_number, Donation.notes], search)
        stmt = apply_date_range(stmt, Donation.donation_date, date_from, date_to)
        stmt = apply_sorting(
            stmt, Donation, sort, {"id", "amount", "donation_date", "status", "created_at", "reference_number"},
            default="donation_date", default_order="desc",
        )
        return paginate(self.db, stmt, params)
