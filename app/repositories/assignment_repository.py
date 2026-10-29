from datetime import date

from sqlalchemy import func, select

from app.core.constants import LIVE_ASSIGNMENT_STATUSES
from app.models.volunteer_assignment import VolunteerAssignment as VA
from app.repositories import BaseRepository
from app.utils.enums import AssignmentStatus
from app.utils.filtering import apply_date_range, apply_equals
from app.utils.pagination import PaginationParams, paginate
from app.utils.sorting import SortParams, apply_sorting


class AssignmentRepository(BaseRepository[VA]):
    model = VA

    def find_conflicts(self, volunteer_id: int, start: date, end: date, exclude_id: int | None = None) -> list[VA]:
        """Live assignments of the volunteer whose date range overlaps [start, end]."""
        stmt = select(VA).where(
            VA.volunteer_id == volunteer_id, VA.status.in_(LIVE_ASSIGNMENT_STATUSES), VA.start_date <= end, VA.end_date >= start
        )
        if exclude_id:
            stmt = stmt.where(VA.id != exclude_id)
        return list(self.db.scalars(stmt).all())

    def list_assignments(
        self, params: PaginationParams, sort: SortParams, *, volunteer_id: int | None = None, project_id: int | None = None,
        status: AssignmentStatus | None = None, date_from: date | None = None, date_to: date | None = None,
    ):
        stmt = apply_equals(select(VA), VA, volunteer_id=volunteer_id, project_id=project_id, status=status)
        stmt = apply_date_range(stmt, VA.start_date, date_from, date_to)
        stmt = apply_sorting(stmt, VA, sort, {"id", "start_date", "end_date", "status", "hours_completed", "created_at"}, default="id", default_order="desc")
        return paginate(self.db, stmt, params)

    def project_ids_for_volunteer(self, volunteer_id: int) -> set[int]:
        rows = self.db.scalars(select(VA.project_id).where(VA.volunteer_id == volunteer_id, VA.status != AssignmentStatus.CANCELLED))
        return set(rows.all())

    def total_hours(self, assignment_id: int) -> float:
        from app.models.attendance import Attendance

        return self.db.scalar(select(func.coalesce(func.sum(Attendance.hours), 0)).where(Attendance.assignment_id == assignment_id)) or 0
