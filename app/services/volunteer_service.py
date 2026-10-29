from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import Permission, has_permission
from app.db.session import transaction
from app.models.user import User
from app.models.volunteer import Volunteer
from app.repositories.user_repository import UserRepository
from app.repositories.volunteer_repository import VolunteerRepository
from app.schemas.volunteer import VolunteerCreate, VolunteerOut, VolunteerUpdate
from app.services.audit_service import AuditService, diff, snapshot
from app.utils.enums import Role, VolunteerStatus
from app.utils.pagination import PaginationParams
from app.utils.sorting import SortParams

AUDIT_FIELDS = ["full_name", "email", "phone", "skills", "availability", "status", "experience"]


def _join_skills(skills: list[str] | None) -> str | None:
    if not skills:
        return None
    seen, out = set(), []
    for s in skills:
        s = s.strip()
        if s and s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
    return ",".join(out) or None


def to_out(v: Volunteer) -> VolunteerOut:
    data = {c.name: getattr(v, c.name) for c in Volunteer.__table__.columns}
    data["skills"] = [s for s in (v.skills or "").split(",") if s]
    return VolunteerOut.model_validate(data)


class VolunteerService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = VolunteerRepository(db)
        self.audit = AuditService(db)

    def _is_staff(self, actor: User) -> bool:
        return has_permission(actor.role, Permission.VOLUNTEERS_READ)

    def get_for_actor(self, actor: User, volunteer_id: int) -> Volunteer:
        v = self.repo.get(volunteer_id)
        if not v:
            raise NotFoundError("Volunteer not found")
        if self._is_staff(actor) or v.user_id == actor.id:
            return v
        raise ForbiddenError("You do not have access to this volunteer profile")

    def me(self, actor: User) -> Volunteer:
        v = self.repo.get_by_user_id(actor.id)
        if not v:
            raise NotFoundError("No volunteer profile is linked to your account")
        return v

    def create(self, actor: User, data: VolunteerCreate) -> Volunteer:
        email = data.email.lower()
        if self.repo.get_by_email(email):
            raise ConflictError("A volunteer with this email already exists")
        if data.user_id is not None:
            if not UserRepository(self.db).get(data.user_id):
                raise NotFoundError("Linked user not found")
            if self.repo.get_by_user_id(data.user_id):
                raise ConflictError("That user already has a volunteer profile")
        payload = data.model_dump(exclude={"skills"})
        payload["email"] = email
        with transaction(self.db):
            v = self.repo.add(Volunteer(**payload, skills=_join_skills(data.skills)))
            self.audit.log(actor, "volunteer.registered", "volunteer", v.id, snapshot(v, AUDIT_FIELDS))
        return v

    def register_self(self, actor: User, data: VolunteerCreate) -> Volunteer:
        if actor.role != Role.VOLUNTEER:
            raise ForbiddenError("Only volunteer accounts can self-register a volunteer profile")
        if self.repo.get_by_user_id(actor.id):
            raise ConflictError("You already have a volunteer profile")
        if data.email.lower() != actor.email.lower():
            raise BusinessRuleError("The profile email must match your account email")
        data = data.model_copy(update={"user_id": actor.id})
        return self.create(actor, data)

    def update(self, actor: User, volunteer_id: int, data: VolunteerUpdate) -> Volunteer:
        changes = data.model_dump(exclude_unset=True)
        with transaction(self.db):
            v = self.get_for_actor(actor, volunteer_id)
            if not has_permission(actor.role, Permission.VOLUNTEERS_WRITE) and "status" in changes:
                raise ForbiddenError("Only staff can change a volunteer's status")
            if "skills" in changes:
                changes["skills"] = _join_skills(changes["skills"])
            if changes.get("status") is None:
                changes.pop("status", None)
            before = snapshot(v, AUDIT_FIELDS)
            for k, val in changes.items():
                setattr(v, k, val)
            self.audit.log(actor, "volunteer.updated", "volunteer", v.id, diff(before, snapshot(v, AUDIT_FIELDS)))
        return v

    def list_volunteers(
        self, params: PaginationParams, sort: SortParams, *, search: str | None, status: VolunteerStatus | None,
        skill: str | None, availability: str | None,
    ):
        return self.repo.list_volunteers(params, sort, search=search, status=status, skill=skill, availability=availability)
