from datetime import date

from sqlalchemy import select

from app.models.attendance import Attendance
from app.repositories import BaseRepository
from app.utils.enums import AttendanceStatus
from app.utils.filtering import apply_date_range, apply_equals
from app.utils.pagination import PaginationParams, paginate
from app.utils.sorting import SortParams, apply_sorting


class AttendanceRepository(BaseRepository[Attendance]):
    model = Attendance

    def get_for_day(self, assignment_id: int, day: date) -> Attendance | None:
        return self.db.scalar(select(Attendance).where(Attendance.assignment_id == assignment_id, Attendance.attendance_date == day))

    def list_attendance(
        self, params: PaginationParams, sort: SortParams, *, assignment_ids: list[int] | None = None, assignment_id: int | None = None,
        status: AttendanceStatus | None = None, date_from: date | None = None, date_to: date | None = None,
    ):
        stmt = apply_equals(select(Attendance), Attendance, assignment_id=assignment_id, status=status)
        if assignment_ids is not None:
            stmt = stmt.where(Attendance.assignment_id.in_(assignment_ids))
        stmt = apply_date_range(stmt, Attendance.attendance_date, date_from, date_to)
        stmt = apply_sorting(stmt, Attendance, sort, {"id", "attendance_date", "hours", "status"}, default="attendance_date", default_order="desc")
        return paginate(self.db, stmt, params)
