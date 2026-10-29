from datetime import date

from sqlalchemy import select

from app.models.beneficiary_assistance import BeneficiaryAssistance as BA
from app.repositories import BaseRepository
from app.utils.filtering import apply_date_range, apply_equals
from app.utils.pagination import PaginationParams, paginate
from app.utils.sorting import SortParams, apply_sorting


class AssistanceRepository(BaseRepository[BA]):
    model = BA

    def list_assistance(
        self, params: PaginationParams, sort: SortParams, *, beneficiary_id: int | None = None, project_id: int | None = None,
        resource_id: int | None = None, date_from: date | None = None, date_to: date | None = None,
    ):
        stmt = apply_equals(select(BA), BA, beneficiary_id=beneficiary_id, project_id=project_id, resource_id=resource_id)
        stmt = apply_date_range(stmt, BA.distribution_date, date_from, date_to)
        stmt = apply_sorting(stmt, BA, sort, {"id", "distribution_date", "quantity", "created_at"}, default="distribution_date", default_order="desc")
        return paginate(self.db, stmt, params)
