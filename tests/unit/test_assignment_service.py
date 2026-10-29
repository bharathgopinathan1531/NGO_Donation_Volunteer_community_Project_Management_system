from datetime import timedelta
from decimal import Decimal

import pytest

from app.core.exceptions import BusinessRuleError, ConflictError, ForbiddenError, NotFoundError
from app.schemas.assignment import AssignmentCreate, AssignmentUpdate
from app.schemas.attendance import AttendanceCreate
from app.services.assignment_service import AssignmentService
from app.services.attendance_service import AttendanceService
from app.utils.enums import AssignmentStatus, ProjectStatus, Role, VolunteerStatus
from app.utils.pagination import PaginationParams
from app.utils.sorting import SortParams
from tests.unit.factories import TODAY, mk_project, mk_volunteer


def window(a, b):
    return dict(start_date=TODAY + timedelta(days=a), end_date=TODAY + timedelta(days=b))


def create(svc, actor, vol, project, a=0, b=10, role="Helper"):
    return svc.create(actor, AssignmentCreate(volunteer_id=vol.id, project_id=project.id, responsibility=role, **window(a, b)))


@pytest.fixture()
def setup(db, make_user):
    return make_user(Role.VOLUNTEER_COORDINATOR), mk_volunteer(db), mk_project(db)


def test_assignment_created_and_volunteer_notified(db, setup, make_user):
    coord, vol, project = setup
    user = make_user(Role.VOLUNTEER, "volunteer-user@example.org")
    vol.user_id = user.id
    db.commit()
    a = create(AssignmentService(db), coord, vol, project)
    assert a.status == AssignmentStatus.ASSIGNED and a.hours_completed == 0
    from app.repositories.notification_repository import NotificationRepository

    notes, total = NotificationRepository(db).list_for_user(user.id, PaginationParams())
    assert total == 1 and notes[0].type.value == "volunteer_assignment"


def test_overlapping_assignment_is_rejected_with_conflict_details(db, setup):
    coord, vol, project = setup
    other_project = mk_project(db, name="Other")
    svc = AssignmentService(db)
    first = create(svc, coord, vol, project, 0, 10)
    with pytest.raises(ConflictError) as exc:
        create(svc, coord, vol, other_project, 5, 15)
    assert exc.value.extra["conflicting_assignment_ids"] == [first.id]


def test_back_to_back_assignments_are_allowed(db, setup):
    coord, vol, project = setup
    svc = AssignmentService(db)
    create(svc, coord, vol, project, 0, 10)
    create(svc, coord, vol, project, 11, 20)


def test_cancelled_assignment_frees_the_slot(db, setup):
    coord, vol, project = setup
    svc = AssignmentService(db)
    a = create(svc, coord, vol, project, 0, 10)
    svc.change_status(coord, a.id, AssignmentStatus.CANCELLED)
    create(svc, coord, vol, project, 0, 10)


def test_dates_must_sit_inside_project_period(db, setup):
    coord, vol, project = setup
    with pytest.raises(BusinessRuleError):
        create(AssignmentService(db), coord, vol, project, 0, 200)


def test_inactive_volunteer_and_closed_project_rejected(db, setup):
    coord, vol, project = setup
    svc = AssignmentService(db)
    vol.status = VolunteerStatus.SUSPENDED
    db.commit()
    with pytest.raises(BusinessRuleError):
        create(svc, coord, vol, project)
    vol.status = VolunteerStatus.ACTIVE
    project.status = ProjectStatus.COMPLETED
    db.commit()
    with pytest.raises(BusinessRuleError):
        create(svc, coord, vol, project)


def test_unknown_volunteer(db, setup):
    coord, vol, project = setup
    ghost = vol.__class__(id=999)
    with pytest.raises(NotFoundError):
        create(AssignmentService(db), coord, ghost, project)


def test_update_revalidates_conflicts(db, setup):
    coord, vol, project = setup
    svc = AssignmentService(db)
    create(svc, coord, vol, project, 0, 10)
    second = create(svc, coord, vol, project, 11, 20)
    with pytest.raises(ConflictError):
        svc.update(coord, second.id, AssignmentUpdate(start_date=TODAY + timedelta(days=5)))


def test_attendance_accumulates_hours_and_activates_assignment(db, setup):
    coord, vol, project = setup
    asvc, att = AssignmentService(db), AttendanceService(db)
    a = create(asvc, coord, vol, project, -5, 10)
    att.record(coord, AttendanceCreate(assignment_id=a.id, attendance_date=TODAY - timedelta(days=2), hours="3.5"))
    rec = att.record(coord, AttendanceCreate(assignment_id=a.id, attendance_date=TODAY - timedelta(days=1), hours="2"))
    assert a.hours_completed == Decimal("5.50") and a.status == AssignmentStatus.ACTIVE
    att_update = __import__("app.schemas.attendance", fromlist=["AttendanceUpdate"]).AttendanceUpdate
    att.update(coord, rec.id, att_update(hours="4"))
    assert a.hours_completed == Decimal("7.50")


def test_attendance_rules(db, setup):
    coord, vol, project = setup
    asvc, att = AssignmentService(db), AttendanceService(db)
    a = create(asvc, coord, vol, project, -5, 10)
    day = TODAY - timedelta(days=1)
    att.record(coord, AttendanceCreate(assignment_id=a.id, attendance_date=day, hours="1"))
    with pytest.raises(ConflictError):  # one record per day
        att.record(coord, AttendanceCreate(assignment_id=a.id, attendance_date=day, hours="1"))
    with pytest.raises(BusinessRuleError):  # outside the assignment
        att.record(coord, AttendanceCreate(assignment_id=a.id, attendance_date=TODAY - timedelta(days=30), hours="1"))
    with pytest.raises(BusinessRuleError):  # future
        att.record(coord, AttendanceCreate(assignment_id=a.id, attendance_date=TODAY + timedelta(days=3), hours="1"))
    with pytest.raises(ValueError):  # present needs hours
        AttendanceCreate(assignment_id=a.id, attendance_date=day, hours="0")


def test_volunteer_only_sees_own_assignments(db, setup, make_user):
    coord, vol, project = setup
    user = make_user(Role.VOLUNTEER, "mine@example.org")
    vol.user_id = user.id
    db.commit()
    svc = AssignmentService(db)
    mine = create(svc, coord, vol, project, 0, 5)
    other_vol = mk_volunteer(db, "other@example.org")
    theirs = create(svc, coord, other_vol, project, 0, 5)
    items, total = svc.list_assignments(user, PaginationParams(), SortParams(), volunteer_id=None, project_id=None, status=None, date_from=None, date_to=None)
    assert [i.id for i in items] == [mine.id]
    with pytest.raises(ForbiddenError):
        svc.get_for_actor(user, theirs.id)


def test_completed_assignment_is_history_and_immutable(db, setup):
    coord, vol, project = setup
    svc = AssignmentService(db)
    a = create(svc, coord, vol, project, -5, 5)
    svc.change_status(coord, a.id, AssignmentStatus.ACTIVE)
    svc.change_status(coord, a.id, AssignmentStatus.COMPLETED)
    with pytest.raises(BusinessRuleError):
        svc.change_status(coord, a.id, AssignmentStatus.ACTIVE)
    with pytest.raises(BusinessRuleError):
        svc.update(coord, a.id, AssignmentUpdate(responsibility="New"))
