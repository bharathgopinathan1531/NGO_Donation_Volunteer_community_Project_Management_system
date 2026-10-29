from datetime import date

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.db.session import transaction
from app.models.beneficiary_assistance import BeneficiaryAssistance
from app.models.user import User
from app.repositories.assistance_repository import AssistanceRepository
from app.repositories.beneficiary_repository import BeneficiaryRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.resource_allocation_repository import ResourceAllocationRepository
from app.repositories.resource_repository import ResourceRepository
from app.schemas.beneficiary_assistance import AssistanceCreate
from app.services.audit_service import AuditService
from app.utils.date_utils import today
from app.utils.enums import ProjectStatus
from app.utils.pagination import PaginationParams
from app.utils.sorting import SortParams

DISTRIBUTION_STATUSES = {ProjectStatus.APPROVED, ProjectStatus.ACTIVE}


class AssistanceService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AssistanceRepository(db)
        self.beneficiaries = BeneficiaryRepository(db)
        self.projects = ProjectRepository(db)
        self.resources = ResourceRepository(db)
        self.allocations = ResourceAllocationRepository(db)
        self.audit = AuditService(db)

    def record(self, actor: User, data: AssistanceCreate) -> BeneficiaryAssistance:
        if data.distribution_date > today():
            raise BusinessRuleError("Distribution date cannot be in the future")
        with transaction(self.db):
            b = self.beneficiaries.get(data.beneficiary_id)
            if not b:
                raise NotFoundError("Beneficiary not found")
            p = self.projects.get(data.project_id)
            if not p:
                raise NotFoundError("Project not found")
            if p.status not in DISTRIBUTION_STATUSES:
                raise BusinessRuleError(f"Assistance can only be recorded for approved or active projects (this one is '{p.status.value}')")
            if not self.beneficiaries.is_mapped(b.id, p.id):
                raise BusinessRuleError("The beneficiary is not mapped to this project; map them first")
            if data.resource_id is not None:
                if not self.resources.get(data.resource_id):
                    raise NotFoundError("Resource not found")
                if data.quantity <= 0:
                    raise BusinessRuleError("quantity must be positive when a resource is distributed")
                # a project can only hand out what was allocated to it and not yet given away
                allocated = self.allocations.allocated_total(data.resource_id, p.id)
                given = self.allocations.distributed_total(data.resource_id, p.id)
                if given + data.quantity > allocated:
                    raise BusinessRuleError(
                        f"Only {allocated - given} unit(s) of this resource remain allocated to the project",
                        extra={"allocated": allocated, "already_distributed": given, "requested": data.quantity},
                    )
            elif data.quantity != 0:
                raise BusinessRuleError("quantity must be 0 unless a resource_id is given")
            rec = self.repo.add(BeneficiaryAssistance(**data.model_dump(), recorded_by=actor.id))
            self.audit.log(
                actor, "assistance.recorded", "beneficiary_assistance", rec.id,
                {"beneficiary_id": b.id, "project_id": p.id, "resource_id": data.resource_id, "quantity": data.quantity,
                 "type": data.assistance_type, "date": data.distribution_date},
            )
        return rec

    def list_assistance(
        self, params: PaginationParams, sort: SortParams, *, beneficiary_id: int | None, project_id: int | None,
        resource_id: int | None, date_from: date | None, date_to: date | None,
    ):
        return self.repo.list_assistance(
            params, sort, beneficiary_id=beneficiary_id, project_id=project_id, resource_id=resource_id, date_from=date_from, date_to=date_to
        )
