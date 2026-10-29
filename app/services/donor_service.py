from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import Permission, has_permission
from app.db.session import transaction
from app.models.donor import Donor
from app.models.user import User
from app.repositories.donation_repository import DonationRepository
from app.repositories.donor_repository import DonorRepository
from app.repositories.user_repository import UserRepository
from app.schemas.donor import DonorCreate, DonorUpdate
from app.services.audit_service import AuditService, diff, snapshot
from app.utils.enums import DonorStatus, DonorType
from app.utils.pagination import PaginationParams
from app.utils.sorting import SortParams

AUDIT_FIELDS = ["name", "donor_type", "status", "email", "phone", "address", "city", "country", "tax_id", "contact_person", "notes"]


class DonorService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DonorRepository(db)
        self.donations = DonationRepository(db)
        self.audit = AuditService(db)

    # ------------------------------------------------------------------ access control
    def get_for_actor(self, actor: User, donor_id: int) -> Donor:
        """Staff with donors:read see everyone; a donor-role user sees only their own profile."""
        donor = self.repo.get(donor_id)
        if not donor:
            raise NotFoundError("Donor not found")
        if has_permission(actor.role, Permission.DONORS_READ):
            return donor
        if has_permission(actor.role, Permission.DONORS_READ_OWN) and donor.user_id == actor.id:
            return donor
        raise ForbiddenError("You do not have access to this donor's information")

    def me(self, actor: User) -> Donor:
        donor = self.repo.get_by_user_id(actor.id)
        if not donor:
            raise NotFoundError("No donor profile is linked to your account")
        return donor

    # ------------------------------------------------------------------ commands
    def create(self, actor: User, data: DonorCreate) -> Donor:
        payload = data.model_dump()
        if payload.get("email"):
            payload["email"] = payload["email"].lower()
            if self.repo.get_by_email(payload["email"]):
                raise ConflictError("A donor with this email already exists")
        if payload.get("user_id") is not None:
            if not UserRepository(self.db).get(payload["user_id"]):
                raise NotFoundError("Linked user not found")
            if self.repo.get_by_user_id(payload["user_id"]):
                raise ConflictError("That user already has a donor profile")
        with transaction(self.db):
            donor = self.repo.add(Donor(**payload))
            self.audit.log(actor, "donor.created", "donor", donor.id, snapshot(donor, AUDIT_FIELDS))
        return donor

    def update(self, actor: User, donor_id: int, data: DonorUpdate) -> Donor:
        changes = data.model_dump(exclude_unset=True)
        with transaction(self.db):
            donor = self.repo.get(donor_id)
            if not donor:
                raise NotFoundError("Donor not found")
            if changes.get("email"):
                changes["email"] = changes["email"].lower()
                other = self.repo.get_by_email(changes["email"])
                if other and other.id != donor.id:
                    raise ConflictError("A donor with this email already exists")
            before = snapshot(donor, AUDIT_FIELDS)
            for k, v in changes.items():
                setattr(donor, k, v)
            self.audit.log(actor, "donor.updated", "donor", donor.id, diff(before, snapshot(donor, AUDIT_FIELDS)))
        return donor

    # ------------------------------------------------------------------ queries
    def list_donors(
        self, params: PaginationParams, sort: SortParams, *, search: str | None, donor_type: DonorType | None,
        status: DonorStatus | None, city: str | None, country: str | None,
    ):
        return self.repo.list_donors(params, sort, search=search, donor_type=donor_type, status=status, city=city, country=country)

    def donation_history(self, actor: User, donor_id: int, params: PaginationParams, sort: SortParams, **filters):
        donor = self.get_for_actor(actor, donor_id)
        return self.donations.list_donations(params, sort, donor_id=donor.id, **filters)
