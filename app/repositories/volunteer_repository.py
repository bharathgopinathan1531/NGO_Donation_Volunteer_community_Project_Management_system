from sqlalchemy import select

from app.models.volunteer import Volunteer
from app.repositories import BaseRepository
from app.utils.enums import VolunteerStatus
from app.utils.filtering import apply_equals, apply_search
from app.utils.pagination import PaginationParams, paginate
from app.utils.sorting import SortParams, apply_sorting


class VolunteerRepository(BaseRepository[Volunteer]):
    model = Volunteer

    def get_by_email(self, email: str) -> Volunteer | None:
        return self.db.scalar(select(Volunteer).where(Volunteer.email == email.lower()))

    def get_by_user_id(self, user_id: int) -> Volunteer | None:
        return self.db.scalar(select(Volunteer).where(Volunteer.user_id == user_id))

    def list_volunteers(
        self, params: PaginationParams, sort: SortParams, *, search: str | None, status: VolunteerStatus | None,
        skill: str | None, availability: str | None,
    ):
        stmt = apply_equals(select(Volunteer), Volunteer, status=status)
        stmt = apply_search(stmt, [Volunteer.full_name, Volunteer.email, Volunteer.phone], search)
        stmt = apply_search(stmt, [Volunteer.skills], skill)
        stmt = apply_search(stmt, [Volunteer.availability], availability)
        stmt = apply_sorting(stmt, Volunteer, sort, {"id", "full_name", "email", "status", "created_at"})
        return paginate(self.db, stmt, params)
