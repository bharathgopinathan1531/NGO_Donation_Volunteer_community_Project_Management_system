from datetime import date

from sqlalchemy import func, select

from app.models.beneficiary_assistance import BeneficiaryAssistance
from app.models.resource_allocation import ResourceAllocation
from app.repositories import BaseRepository
from app.utils.filtering import apply_date_range, apply_equals
from app.utils.pagination import PaginationParams, paginate
from app.utils.sorting import SortParams, apply_sorting


class ResourceAllocationRepository(BaseRepository[ResourceAllocation]):
    model = ResourceAllocation

    def allocated_total(self, resource_id: int, project_id: int) -> int:
        return self.db.scalar(
            select(func.coalesce(func.sum(ResourceAllocation.quantity), 0)).where(
                ResourceAllocation.resource_id == resource_id, ResourceAllocation.project_id == project_id
            )
        ) or 0

    def distributed_total(self, resource_id: int, project_id: int) -> int:
        return self.db.scalar(
            select(func.coalesce(func.sum(BeneficiaryAssistance.quantity), 0)).where(
                BeneficiaryAssistance.resource_id == resource_id, BeneficiaryAssistance.project_id == project_id
            )
        ) or 0

    def list_allocations(
        self, params: PaginationParams, sort: SortParams, *, resource_id: int | None = None, project_id: int | None = None,
        date_from: date | None = None, date_to: date | None = None,
    ):
        stmt = apply_equals(select(ResourceAllocation), ResourceAllocation, resource_id=resource_id, project_id=project_id)
        stmt = apply_date_range(stmt, ResourceAllocation.allocated_at, date_from, date_to)
        stmt = apply_sorting(stmt, ResourceAllocation, sort, {"id", "allocated_at", "quantity"}, default="id", default_order="desc")
        return paginate(self.db, stmt, params)
