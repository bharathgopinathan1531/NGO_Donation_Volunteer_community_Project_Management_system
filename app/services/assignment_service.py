from datetime import date

from sqlalchemy.orm import Session

from app.core.constants import ASSIGNMENT_TRANSITIONS, LIVE_ASSIGNMENT_STATUSES, PROJECT_CLOSED_STATUSES, assert_transition
from app.core.exceptions import BusinessRuleError, ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import Permission, has_permission
from app.db.session import transaction
from app.models.user import User
from app.models.volunteer_assignment import VolunteerAssignment
from app.repositories.assignment_repository import AssignmentRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.volunteer_repository import VolunteerRepository
from app.schemas.assignment import AssignmentCreate, AssignmentUpdate
from app.services.audit_service import AuditService, diff, snapshot
from app.services.notification_service import NotificationService
from app.utils.enums import AssignmentStatus, NotificationType, VolunteerStatus
from app.utils.money import money
from app.utils.pagination import PaginationParams
from app.utils.sorting import SortParams

AUDIT_FIELDS = ["volunteer_id", "project_id", "responsibility", "start_date", "end_date", "status", "hours_completed"]


class AssignmentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AssignmentRepository(db)
        self.volunteers = VolunteerRepository(db)
        self.projects = ProjectRepository(db)
        self.audit = AuditService(db)
        self.notifications = NotificationService(db)

    # ------------------------------------------------------------------ access
    def _own_volunteer_id(self, actor: User) -> int | None:
        v = self.volunteers.get_by_user_id(actor.id)
        return v.id if v else None

    def get_for_actor(self, actor: User, assignment_id: int) -> VolunteerAssignment:
        a = self.repo.get(assignment_id)
        if not a:
            raise NotFoundError("Assignment not found")
        if has_permission(actor.role, Permission.ASSIGNMENTS_READ):
            return a
        if has_permission(actor.role, Permission.ASSIGNMENTS_READ_OWN) and a.volunteer_id == self._own_volunteer_id(actor):
            return a
        raise ForbiddenError("You do not have access to this assignment")

    # ------------------------------------------------------------------ validation helpers
    def _validate_window(self, project, start: date, end: date) -> None:
        if end < start:
            raise BusinessRuleError("end_date must be on or after start_date")
        if start < project.start_date or end > project.end_date:
            raise BusinessRuleError(
                f"Assignment dates must fall within the project period ({project.start_date} to {project.end_date})"
            )

    def _assert_no_conflict(self, volunteer_id: int, start: date, end: date, exclude_id: int | None = None) -> None:
        conflicts = self.repo.find_conflicts(volunteer_id, start, end, exclude_id)
        if conflicts:
            raise ConflictError(
                "Volunteer already has an overlapping assignment in this period",
                extra={"conflicting_assignment_ids": [c.id for c in conflicts]},
            )

    # ------------------------------------------------------------------ commands
    def create(self, actor: User, data: AssignmentCreate) -> VolunteerAssignment:
        with transaction(self.db):
            volunteer = self.volunteers.get(data.volunteer_id, for_update=True)
            if not volunteer:
                raise NotFoundError("Volunteer not found")
            if volunteer.status != VolunteerStatus.ACTIVE:
                raise BusinessRuleError(f"Volunteer is {volunteer.status.value} and cannot be assigned")
            project = self.projects.get(data.project_id)
            if not project:
                raise NotFoundError("Project not found")
            if project.status in PROJECT_CLOSED_STATUSES:
                raise BusinessRuleError(f"Project is {project.status.value}; volunteers cannot be assigned")
            self._validate_window(project, data.start_date, data.end_date)
            self._assert_no_conflict(volunteer.id, data.start_date, data.end_date)
            a = self.repo.add(
                VolunteerAssignment(**data.model_dump(), status=AssignmentStatus.ASSIGNED, hours_completed=money(0), assigned_by=actor.id)
            )
            self.notifications.notify(
                [volunteer.user_id], NotificationType.VOLUNTEER_ASSIGNMENT, "New volunteer assignment",
                f"You have been assigned to project '{project.name}' as {a.responsibility} "
                f"({a.start_date.isoformat()} to {a.end_date.isoformat()}).",
                entity="assignment", entity_id=a.id, dedupe_key=f"assignment:{a.id}",
            )
            self.audit.log(actor, "assignment.created", "assignment", a.id, snapshot(a, AUDIT_FIELDS))
        return a

    def update(self, actor: User, assignment_id: int, data: AssignmentUpdate) -> VolunteerAssignment:
        changes = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
        with transaction(self.db):
            a = self.repo.get(assignment_id, for_update=True)
            if not a:
                raise NotFoundError("Assignment not found")
            if a.status not in LIVE_ASSIGNMENT_STATUSES:
                raise BusinessRuleError(f"A {a.status.value} assignment cannot be edited")
            start, end = changes.get("start_date", a.start_date), changes.get("end_date", a.end_date)
            if "start_date" in changes or "end_date" in changes:
                self._validate_window(self.projects.get(a.project_id), start, end)
                self._assert_no_conflict(a.volunteer_id, start, end, exclude_id=a.id)
            before = snapshot(a, AUDIT_FIELDS)
            for k, v in changes.items():
                setattr(a, k, v)
            self.audit.log(actor, "assignment.updated", "assignment", a.id, diff(before, snapshot(a, AUDIT_FIELDS)))
        return a

    def change_status(self, actor: User, assignment_id: int, target: AssignmentStatus) -> VolunteerAssignment:
        with transaction(self.db):
            a = self.repo.get(assignment_id, for_update=True)
            if not a:
                raise NotFoundError("Assignment not found")
            assert_transition(ASSIGNMENT_TRANSITIONS, a.status, target, "assignment status")
            old = a.status
            a.status = target
            self.db.flush()
            a.hours_completed = money(self.repo.total_hours(a.id))
            self.audit.log(
                actor, f"assignment.{target.value}", "assignment", a.id,
                {"status": {"from": old, "to": target}, "hours_completed": a.hours_completed},
            )
        return a

    def list_assignments(
        self, actor: User, params: PaginationParams, sort: SortParams, *, volunteer_id: int | None, project_id: int | None,
        status: AssignmentStatus | None, date_from: date | None, date_to: date | None,
    ):
        if not has_permission(actor.role, Permission.ASSIGNMENTS_READ):
            own = self._own_volunteer_id(actor)
            if own is None:
                return [], 0
            if volunteer_id is not None and volunteer_id != own:
                raise ForbiddenError("You can only list your own assignments")
            volunteer_id = own
        return self.repo.list_assignments(
            params, sort, volunteer_id=volunteer_id, project_id=project_id, status=status, date_from=date_from, date_to=date_to
        )
