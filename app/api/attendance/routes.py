from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_permissions
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.attendance import AttendanceCreate, AttendanceOut, AttendanceUpdate
from app.schemas.common import Page
from app.services.attendance_service import AttendanceService
from app.utils.enums import AttendanceStatus
from app.utils.pagination import PaginationParams, build_page, pagination_params
from app.utils.sorting import SortParams, sort_params

router = APIRouter(prefix="/attendance", tags=["Attendance"])
writer = require_permissions(Permission.ATTENDANCE_WRITE)


@router.post("", response_model=AttendanceOut, status_code=status.HTTP_201_CREATED, summary="Record attendance and hours for an assignment day")
def record_attendance(payload: AttendanceCreate, actor: User = Depends(writer), db: Session = Depends(get_db)):
    return AttendanceService(db).record(actor, payload)


@router.get("", response_model=Page[AttendanceOut])
def list_attendance(
    assignment_id: int | None = None, status: AttendanceStatus | None = None, date_from: date | None = None, date_to: date | None = None,
    params: PaginationParams = Depends(pagination_params), sort: SortParams = Depends(sort_params),
    actor: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    items, total = AttendanceService(db).list_attendance(
        actor, params, sort, assignment_id=assignment_id, status=status, date_from=date_from, date_to=date_to
    )
    return build_page([AttendanceOut.model_validate(i) for i in items], total, params)


@router.patch("/{attendance_id}", response_model=AttendanceOut, summary="Correct an attendance record")
def update_attendance(attendance_id: int, payload: AttendanceUpdate, actor: User = Depends(writer), db: Session = Depends(get_db)):
    return AttendanceService(db).update(actor, attendance_id, payload)
