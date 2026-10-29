from sqlalchemy import select

from app.models.donor import Donor
from app.repositories import BaseRepository
from app.utils.enums import DonorStatus, DonorType
from app.utils.filtering import apply_equals, apply_search
from app.utils.pagination import PaginationParams, paginate
from app.utils.sorting import SortParams, apply_sorting


class DonorRepository(BaseRepository[Donor]):
    model = Donor

    def get_by_email(self, email: str) -> Donor | None:
        return self.db.scalar(select(Donor).where(Donor.email == email.lower()))

    def get_by_user_id(self, user_id: int) -> Donor | None:
        return self.db.scalar(select(Donor).where(Donor.user_id == user_id))

    def list_donors(
        self, params: PaginationParams, sort: SortParams, *, search: str | None, donor_type: DonorType | None,
        status: DonorStatus | None, city: str | None, country: str | None,
    ):
        stmt = apply_equals(select(Donor), Donor, donor_type=donor_type, status=status, city=city, country=country)
        stmt = apply_search(stmt, [Donor.name, Donor.email, Donor.phone, Donor.contact_person], search)
        stmt = apply_sorting(stmt, Donor, sort, {"id", "name", "created_at", "donor_type", "status", "city", "country"})
        return paginate(self.db, stmt, params)
