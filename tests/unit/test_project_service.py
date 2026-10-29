from datetime import timedelta
from decimal import Decimal

import pytest

from app.core.exceptions import BusinessRuleError, ForbiddenError, NotFoundError
from app.schemas.assignment import AssignmentCreate
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.approval_service import ApprovalService
from app.services.assignment_service import AssignmentService
from app.services.project_service import ProjectService
from app.utils.enums import AssignmentStatus, MilestoneStatus, ProjectStatus, Role
from app.utils.pagination import PaginationParams
from app.utils.sorting import SortParams
from tests.unit.factories import TODAY, mk_milestone, mk_project, mk_volunteer


def pc(**kw):
    base = dict(name="Well Digging", start_date=TODAY, end_date=TODAY + timedelta(days=90), budget="1000")
    base.update(kw)
    return ProjectCreate(**base)


def test_create_defaults_to_planning_with_actor_as_manager(db, make_user):
    mgr = make_user(Role.NGO_MANAGER)
    p = ProjectService(db).create(mgr, pc())
    assert p.status == ProjectStatus.PLANNING and p.manager_id == mgr.id and p.budget == Decimal("1000.00")


def test_manager_must_be_staff(db, make_user):
    admin, vol = make_user(Role.SUPER_ADMIN), make_user(Role.VOLUNTEER)
    with pytest.raises(BusinessRuleError):
        ProjectService(db).create(admin, pc(manager_id=vol.id))


def test_unknown_campaign_rejected(db, make_user):
    with pytest.raises(NotFoundError):
        ProjectService(db).create(make_user(Role.NGO_MANAGER), pc(campaign_id=404))


def test_project_cannot_be_activated_before_approval(db, make_user):
    admin = make_user(Role.SUPER_ADMIN)
    svc = ProjectService(db)
    p = svc.create(admin, pc())
    with pytest.raises(BusinessRuleError):
        svc.change_status(admin, p.id, ProjectStatus.ACTIVE)  # planning -> active is not a legal transition
    with pytest.raises(BusinessRuleError):
        svc.change_status(admin, p.id, ProjectStatus.APPROVED)  # only the approval workflow may do this


def test_activation_after_approval_and_pause_resume(db, make_user):
    admin = make_user(Role.SUPER_ADMIN)
    svc, appr = ProjectService(db), ApprovalService(db)
    p = svc.create(admin, pc())
    appr.submit(admin, p.id, None)
    appr.approve(admin, p.id, None)
    assert svc.change_status(admin, p.id, ProjectStatus.ACTIVE).status == ProjectStatus.ACTIVE
    assert svc.change_status(admin, p.id, ProjectStatus.ON_HOLD).status == ProjectStatus.ON_HOLD
    assert svc.change_status(admin, p.id, ProjectStatus.ACTIVE).status == ProjectStatus.ACTIVE


def test_cannot_complete_with_unfinished_milestones(db, make_user):
    admin = make_user(Role.SUPER_ADMIN)
    p = mk_project(db, status=ProjectStatus.ACTIVE)
    ms = mk_milestone(db, p)
    svc = ProjectService(db)
    with pytest.raises(BusinessRuleError):
        svc.change_status(admin, p.id, ProjectStatus.COMPLETED)
    ms.status = MilestoneStatus.COMPLETED
    db.commit()
    # approval history is required to *activate*, completion only needs finished milestones
    assert svc.change_status(admin, p.id, ProjectStatus.COMPLETED).status == ProjectStatus.COMPLETED


def test_cancelling_a_project_cancels_live_assignments(db, make_user):
    admin = make_user(Role.SUPER_ADMIN)
    p, vol = mk_project(db, status=ProjectStatus.ACTIVE), mk_volunteer(db)
    a = AssignmentService(db).create(
        admin, AssignmentCreate(volunteer_id=vol.id, project_id=p.id, responsibility="Helper", start_date=TODAY, end_date=TODAY + timedelta(days=5))
    )
    ProjectService(db).change_status(admin, p.id, ProjectStatus.CANCELLED)
    db.refresh(a)
    assert a.status == AssignmentStatus.CANCELLED


def test_closed_projects_cannot_be_edited(db, make_user):
    p = mk_project(db, status=ProjectStatus.COMPLETED)
    with pytest.raises(BusinessRuleError):
        ProjectService(db).update(make_user(Role.SUPER_ADMIN), p.id, ProjectUpdate(name="Renamed"))


def test_budget_cannot_drop_below_spent(db, make_user):
    from app.models.expense import Expense
    from app.utils.enums import ExpenseCategory, ExpenseStatus

    p = mk_project(db, budget="1000.00")
    db.add(Expense(project_id=p.id, category=ExpenseCategory.OTHER, amount=Decimal("600"), expense_date=TODAY, description="x", receipt_reference="r", status=ExpenseStatus.APPROVED))
    db.commit()
    with pytest.raises(BusinessRuleError):
        ProjectService(db).update(make_user(Role.SUPER_ADMIN), p.id, ProjectUpdate(budget="500"))


def test_milestone_completion_summary(db):
    p = mk_project(db)
    mk_milestone(db, p, "A", status=MilestoneStatus.COMPLETED)
    mk_milestone(db, p, "B")
    detail = ProjectService(db).serialize(p)
    assert (detail.milestones_total, detail.milestones_completed, detail.milestone_completion_pct) == (2, 1, 50.0)


def test_volunteer_sees_only_projects_they_are_assigned_to(db, make_user):
    user = make_user(Role.VOLUNTEER, "v@example.org")
    vol = mk_volunteer(db, "v@example.org")
    vol.user_id = user.id
    db.commit()
    mine, hidden = mk_project(db, name="Mine"), mk_project(db, name="Hidden")
    AssignmentService(db).create(
        make_user(Role.VOLUNTEER_COORDINATOR),
        AssignmentCreate(volunteer_id=vol.id, project_id=mine.id, responsibility="Helper", start_date=TODAY, end_date=TODAY + timedelta(days=3)),
    )
    svc = ProjectService(db)
    items, _ = svc.list_projects(user, PaginationParams(), SortParams(), search=None, status=None, manager_id=None, campaign_id=None, location=None, date_from=None, date_to=None)
    assert [p.name for p in items] == ["Mine"]
    assert svc.get_for_actor(user, mine.id)
    with pytest.raises(ForbiddenError):
        svc.get_for_actor(user, hidden.id)
