from datetime import date

from sqlalchemy.orm import Session

from app.core.constants import LIVE_ASSIGNMENT_STATUSES
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.core.permissions import Permission, has_permission
from app.db.session import transaction
from app.models.attendance import Attendance
from app.models.user import User
from app.repositories.assignment_repository import AssignmentRepository
from app.repositories.attendance_repository import AttendanceRepository
from app.repositories.volunteer_repository import VolunteerRepository
from app.schemas.attendance import AttendanceCreate, AttendanceUpdate
from app.services.audit_service import AuditService
from app.utils.date_utils import today
from app.utils.enums import AssignmentStatus, AttendanceStatus
from app.utils.money import money
from app.utils.pagination import PaginationParams
from app.utils.sorting import SortParams


class AttendanceService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AttendanceRepository(db)
        self.assignments = AssignmentRepository(db)
        self.audit = AuditService(db)

    def _recompute_hours(self, assignment) -> None:
        self.db.flush()
        assignment.hours_completed = money(self.assignments.total_hours(assignment.id))

    @staticmethod
    def _validate_combo(status: AttendanceStatus, hours) -> None:
        if status == AttendanceStatus.PRESENT and hours <= 0:
            raise BusinessRuleError("A 'present' record needs hours > 0")
        if status != AttendanceStatus.PRESENT and hours != 0:
            raise BusinessRuleError("Hours must be 0 unless status is 'present'")

    def record(self, actor: User, data: AttendanceCreate) -> Attendance:
        with transaction(self.db):
            a = self.assignments.get(data.assignment_id, for_update=True)
            if not a:
                raise NotFoundError("Assignment not found")
            if a.status not in LIVE_ASSIGNMENT_STATUSES:
                raise BusinessRuleError(f"Attendance cannot be recorded for a {a.status.value} assignment")
            if not (a.start_date <= data.attendance_date <= a.end_date):
                raise BusinessRuleError("Attendance date is outside the assignment period")
            if data.attendance_date > today():
                raise BusinessRuleError("Attendance cannot be recorded for a future date")
            if self.repo.get_for_day(a.id, data.attendance_date):
                raise ConflictError("Attendance for this assignment and date is already recorded")
            att = self.repo.add(
                Attendance(
                    assignment_id=a.id, attendance_date=data.attendance_date, status=data.status, hours=money(data.hours),
                    notes=data.notes, recorded_by=actor.id,
                )
            )
            if a.status == AssignmentStatus.ASSIGNED:
                a.status = AssignmentStatus.ACTIVE
            self._recompute_hours(a)
            self.audit.log(
                actor, "attendance.recorded", "attendance", att.id,
                {"assignment_id": a.id, "date": att.attendance_date, "status": att.status, "hours": att.hours, "total_hours": a.hours_completed},
            )
        return att

    def update(self, actor: User, attendance_id: int, data: AttendanceUpdate) -> Attendance:
        changes = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None or k == "notes"}
        with transaction(self.db):
            att = self.repo.get(attendance_id)
            if not att:
                raise NotFoundError("Attendance record not found")
            a = self.assignments.get(att.assignment_id, for_update=True)
            if a.status not in LIVE_ASSIGNMENT_STATUSES:
                raise BusinessRuleError(f"Attendance of a {a.status.value} assignment cannot be changed")
            status = changes.get("status", att.status)
            hours = money(changes["hours"]) if "hours" in changes else att.hours
            if "status" in changes and status != AttendanceStatus.PRESENT and "hours" not in changes:
                hours = money(0)
            self._validate_combo(status, hours)
            old = {"status": att.status, "hours": att.hours}
            att.status, att.hours = status, hours
            if "notes" in changes:
                att.notes = changes["notes"]
            self._recompute_hours(a)
            self.audit.log(
                actor, "attendance.updated", "attendance", att.id,
                {"from": old, "to": {"status": att.status, "hours": att.hours}, "total_hours": a.hours_completed},
            )
        return att

    def list_attendance(
        self, actor: User, params: PaginationParams, sort: SortParams, *, assignment_id: int | None, status: AttendanceStatus | None,
        date_from: date | None, date_to: date | None,
    ):
        assignment_ids = None
        if not has_permission(actor.role, Permission.ASSIGNMENTS_READ):
            vol = VolunteerRepository(self.db).get_by_user_id(actor.id)
            if not vol:
                return [], 0
            own, _ = self.assignments.list_assignments(PaginationParams(1, 200), SortParams(), volunteer_id=vol.id)
            assignment_ids = [x.id for x in own] or [-1]
            if assignment_id is not None and assignment_id not in assignment_ids:
                raise NotFoundError("Assignment not found")
        return self.repo.list_attendance(
            params, sort, assignment_ids=assignment_ids, assignment_id=assignment_id, status=status, date_from=date_from, date_to=date_to
        )
