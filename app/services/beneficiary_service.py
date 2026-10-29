from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.permissions import Permission, has_permission
from app.db.session import transaction
from app.models.beneficiary import Beneficiary
from app.models.user import User
from app.repositories.beneficiary_repository import BeneficiaryRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.beneficiary import BeneficiaryCreate, BeneficiaryOut, BeneficiaryUpdate
from app.services.audit_service import AuditService
from app.utils.enums import BeneficiaryCategory
from app.utils.pagination import PaginationParams
from app.utils.sorting import SortParams

SENSITIVE_FIELDS = ("phone", "address", "national_id", "notes")


class BeneficiaryService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = BeneficiaryRepository(db)
        self.projects = ProjectRepository(db)
        self.audit = AuditService(db)

    def serialize(self, actor: User, b: Beneficiary) -> BeneficiaryOut:
        """Sensitive contact / identity fields are redacted unless the caller holds beneficiaries:sensitive."""
        data = {c.name: getattr(b, c.name) for c in Beneficiary.__table__.columns}
        if not has_permission(actor.role, Permission.BENEFICIARIES_SENSITIVE):
            for f in SENSITIVE_FIELDS:
                data[f] = None
        data["project_ids"] = self.repo.project_ids(b.id)
        return BeneficiaryOut.model_validate(data)

    def get(self, beneficiary_id: int) -> Beneficiary:
        b = self.repo.get(beneficiary_id)
        if not b:
            raise NotFoundError("Beneficiary not found")
        return b

    def _check_projects(self, ids: list[int]) -> None:
        for pid in ids:
            if not self.projects.get(pid):
                raise NotFoundError(f"Project {pid} not found")

    def create(self, actor: User, data: BeneficiaryCreate) -> Beneficiary:
        project_ids = sorted(set(data.project_ids))
        self._check_projects(project_ids)
        with transaction(self.db):
            b = self.repo.add(Beneficiary(**data.model_dump(exclude={"project_ids"}), registered_by=actor.id))
            for pid in project_ids:
                self.repo.map_to_project(b.id, pid)
            # sensitive values are deliberately not copied into the audit trail
            self.audit.log(actor, "beneficiary.registered", "beneficiary", b.id, {"category": b.category, "project_ids": project_ids})
        return b

    def update(self, actor: User, beneficiary_id: int, data: BeneficiaryUpdate) -> Beneficiary:
        changes = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
        with transaction(self.db):
            b = self.get(beneficiary_id)
            for k, v in changes.items():
                setattr(b, k, v)
            self.audit.log(actor, "beneficiary.updated", "beneficiary", b.id, {"fields_changed": sorted(changes)})
        return b

    def map_project(self, actor: User, beneficiary_id: int, project_id: int) -> Beneficiary:
        with transaction(self.db):
            b = self.get(beneficiary_id)
            self._check_projects([project_id])
            if self.repo.is_mapped(b.id, project_id):
                raise ConflictError("Beneficiary is already mapped to this project")
            self.repo.map_to_project(b.id, project_id)
            self.audit.log(actor, "beneficiary.mapped", "beneficiary", b.id, {"project_id": project_id})
        return b

    def unmap_project(self, actor: User, beneficiary_id: int, project_id: int) -> Beneficiary:
        with transaction(self.db):
            b = self.get(beneficiary_id)
            if not self.repo.is_mapped(b.id, project_id):
                raise NotFoundError("Beneficiary is not mapped to this project")
            self.repo.unmap_from_project(b.id, project_id)
            self.audit.log(actor, "beneficiary.unmapped", "beneficiary", b.id, {"project_id": project_id})
        return b

    def list_beneficiaries(self, params: PaginationParams, sort: SortParams, *, search: str | None, category: BeneficiaryCategory | None, project_id: int | None):
        return self.repo.list_beneficiaries(params, sort, search=search, category=category, project_id=project_id)
