from datetime import date

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.db.session import transaction
from app.models.resource_allocation import ResourceAllocation
from app.models.user import User
from app.repositories.project_repository import ProjectRepository
from app.repositories.resource_allocation_repository import ResourceAllocationRepository
from app.schemas.resource_allocation import AllocationCreate, AllocationOut
from app.services.audit_service import AuditService
from app.services.resource_service import ResourceService
from app.utils.enums import ProjectStatus, StockTransactionType
from app.utils.pagination import PaginationParams
from app.utils.sorting import SortParams

ALLOCATABLE_STATUSES = {ProjectStatus.APPROVED, ProjectStatus.ACTIVE, ProjectStatus.ON_HOLD}


class ResourceAllocationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ResourceAllocationRepository(db)
        self.projects = ProjectRepository(db)
        self.resources = ResourceService(db)
        self.audit = AuditService(db)

    def serialize(self, a: ResourceAllocation) -> AllocationOut:
        out = AllocationOut.model_validate(a)
        out.distributed_quantity = self.repo.distributed_total(a.resource_id, a.project_id)
        return out

    def allocate(self, actor: User, data: AllocationCreate) -> ResourceAllocation:
        with transaction(self.db):
            p = self.projects.get(data.project_id)
            if not p:
                raise NotFoundError("Project not found")
            if p.status not in ALLOCATABLE_STATUSES:
                raise BusinessRuleError(f"Resources can only be allocated to approved or active projects (this one is '{p.status.value}')")
            self.resources.get(data.resource_id)
            tx = self.resources.apply_movement(
                actor, data.resource_id, StockTransactionType.ALLOCATION, data.quantity, project_id=p.id,
                reason=f"Allocated to project '{p.name}'", reference=data.notes,
            )
            alloc = self.repo.add(
                ResourceAllocation(resource_id=data.resource_id, project_id=p.id, quantity=data.quantity, notes=data.notes, allocated_by=actor.id)
            )
            self.audit.log(
                actor, "resource.allocated", "resource_allocation", alloc.id,
                {"resource_id": data.resource_id, "project_id": p.id, "quantity": data.quantity, "balance_after": tx.balance_after},
            )
        return alloc

    def list_allocations(
        self, params: PaginationParams, sort: SortParams, *, resource_id: int | None, project_id: int | None,
        date_from: date | None, date_to: date | None,
    ):
        return self.repo.list_allocations(params, sort, resource_id=resource_id, project_id=project_id, date_from=date_from, date_to=date_to)
