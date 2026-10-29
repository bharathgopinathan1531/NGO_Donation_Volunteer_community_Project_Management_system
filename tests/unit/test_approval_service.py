import pytest

from app.core.exceptions import BusinessRuleError, ConflictError, ForbiddenError
from app.services.approval_service import ApprovalService
from app.services.project_service import ProjectService
from app.utils.enums import ApprovalAction, ProjectStatus, Role
from app.utils.pagination import PaginationParams
from tests.unit.factories import mk_project


@pytest.fixture()
def setup(db, make_user):
    project = mk_project(db, status=ProjectStatus.PLANNING)
    return make_user(Role.NGO_MANAGER), make_user(Role.SUPER_ADMIN), project


def test_submit_creates_history_and_notifies_approvers(db, setup):
    manager, admin, p = setup
    ApprovalService(db).submit(manager, p.id, "please review")
    from app.repositories.notification_repository import NotificationRepository

    _, total = NotificationRepository(db).list_for_user(admin.id, PaginationParams())
    assert total == 1
    assert ProjectService(db).serialize(p).approval_state == "submitted"


def test_cannot_submit_twice_or_when_not_planning(db, setup):
    manager, _, p = setup
    svc = ApprovalService(db)
    svc.submit(manager, p.id, None)
    with pytest.raises(ConflictError):
        svc.submit(manager, p.id, None)
    active = mk_project(db, name="Active", status=ProjectStatus.ACTIVE)
    with pytest.raises(BusinessRuleError):
        svc.submit(manager, active.id, None)


def test_approve_moves_project_to_approved_and_notifies_submitter(db, setup):
    manager, admin, p = setup
    svc = ApprovalService(db)
    svc.submit(manager, p.id, None)
    svc.approve(admin, p.id, "go")
    assert p.status == ProjectStatus.APPROVED
    from app.repositories.notification_repository import NotificationRepository

    notes, _ = NotificationRepository(db).list_for_user(manager.id, PaginationParams())
    assert notes[0].type.value == "project_approval_decision"


def test_rejection_keeps_planning_and_allows_resubmission(db, setup):
    manager, admin, p = setup
    svc = ApprovalService(db)
    svc.submit(manager, p.id, None)
    svc.reject(admin, p.id, "budget unclear")
    assert p.status == ProjectStatus.PLANNING
    svc.submit(manager, p.id, "fixed budget")
    svc.approve(admin, p.id, None)
    history = svc.history(admin, p.id)
    assert [h.action for h in history] == [ApprovalAction.SUBMITTED, ApprovalAction.REJECTED, ApprovalAction.SUBMITTED, ApprovalAction.APPROVED]
    assert history[1].comments == "budget unclear"


def test_cannot_decide_without_pending_submission(db, setup):
    _, admin, p = setup
    with pytest.raises(BusinessRuleError):
        ApprovalService(db).approve(admin, p.id, None)


def test_manager_cannot_approve_own_submission_but_super_admin_can(db, setup, make_user):
    manager, admin, p = setup
    svc = ApprovalService(db)
    svc.submit(manager, p.id, None)
    with pytest.raises(ForbiddenError):
        svc.approve(manager, p.id, None)
    other_manager = make_user(Role.NGO_MANAGER, "m2@example.org")
    svc.approve(other_manager, p.id, None)
    assert p.status == ProjectStatus.APPROVED


def test_super_admin_may_self_approve(db, make_user):
    admin = make_user(Role.SUPER_ADMIN)
    p = mk_project(db, status=ProjectStatus.PLANNING)
    svc = ApprovalService(db)
    svc.submit(admin, p.id, None)
    svc.approve(admin, p.id, None)
    assert p.status == ProjectStatus.APPROVED


def test_pending_list_only_contains_awaiting_projects(db, setup):
    manager, admin, p = setup
    done = mk_project(db, name="Done", status=ProjectStatus.PLANNING)
    svc = ApprovalService(db)
    svc.submit(manager, p.id, None)
    svc.submit(manager, done.id, None)
    svc.approve(admin, done.id, None)
    items, total = svc.pending(PaginationParams())
    assert total == 1 and items[0].project_id == p.id
