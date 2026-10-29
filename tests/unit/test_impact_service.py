from datetime import timedelta
from decimal import Decimal

import pytest

from app.core.exceptions import NotFoundError
from app.models.attendance import Attendance
from app.models.beneficiary_assistance import BeneficiaryAssistance
from app.models.expense import Expense
from app.models.volunteer_assignment import VolunteerAssignment
from app.schemas.impact import ImpactUpdateCreate
from app.services.impact_service import ImpactService
from app.utils.enums import AttendanceStatus, ExpenseCategory, ExpenseStatus, MilestoneStatus, ProjectStatus, Role
from app.utils.pagination import PaginationParams
from tests.unit.factories import TODAY, mk_beneficiary, mk_milestone, mk_project, mk_resource, mk_volunteer


@pytest.fixture()
def populated(db):
    p = mk_project(db)
    vol, res = mk_volunteer(db), mk_resource(db)
    a = VolunteerAssignment(volunteer_id=vol.id, project_id=p.id, responsibility="x", start_date=TODAY - timedelta(days=5), end_date=TODAY)
    db.add(a)
    db.commit()
    db.add_all([
        Attendance(assignment_id=a.id, attendance_date=TODAY - timedelta(days=2), status=AttendanceStatus.PRESENT, hours=Decimal("4.5")),
        Attendance(assignment_id=a.id, attendance_date=TODAY - timedelta(days=1), status=AttendanceStatus.ABSENT, hours=Decimal("0")),
        Expense(project_id=p.id, category=ExpenseCategory.OTHER, amount=Decimal("300"), expense_date=TODAY, description="d", receipt_reference="r", status=ExpenseStatus.APPROVED),
        Expense(project_id=p.id, category=ExpenseCategory.OTHER, amount=Decimal("50"), expense_date=TODAY, description="d", receipt_reference="r2", status=ExpenseStatus.SUBMITTED),
    ])
    b1, b2 = mk_beneficiary(db, "B1"), mk_beneficiary(db, "B2")
    for b, q in ((b1, 3), (b1, 2), (b2, 4)):
        db.add(BeneficiaryAssistance(beneficiary_id=b.id, project_id=p.id, resource_id=res.id, assistance_type="kit", quantity=q, distribution_date=TODAY))
    mk_milestone(db, p, "done", status=MilestoneStatus.COMPLETED)
    mk_milestone(db, p, "open")
    db.commit()
    return p


def test_live_summary_is_computed_from_records(db, populated):
    s = ImpactService(db).live_summary(populated.id)
    assert s.beneficiaries_served == 2  # distinct beneficiaries, not records
    assert s.volunteer_hours == Decimal("4.50")  # absent rows excluded
    assert s.resources_distributed == 9
    assert s.funds_utilized == Decimal("300.00")  # submitted expenses excluded
    assert s.milestones_achieved == 1 and s.projects_completed == 0


def test_organisation_wide_summary_counts_completed_projects(db, populated):
    mk_project(db, name="Done", status=ProjectStatus.COMPLETED)
    assert ImpactService(db).live_summary().projects_completed == 1


def test_submit_autofills_blank_metrics(db, populated, make_user):
    u = ImpactService(db).submit(make_user(Role.NGO_MANAGER), ImpactUpdateCreate(project_id=populated.id, notes="Q1"))
    assert (u.beneficiaries_served, u.resources_distributed, u.milestones_achieved) == (2, 9, 1)
    assert u.funds_utilized == Decimal("300.00") and u.volunteer_hours == Decimal("4.50") and not u.project_completed


def test_manager_supplied_values_override_live_values(db, populated, make_user):
    u = ImpactService(db).submit(make_user(Role.NGO_MANAGER), ImpactUpdateCreate(project_id=populated.id, beneficiaries_served=120, funds_utilized="12.5"))
    assert u.beneficiaries_served == 120 and u.funds_utilized == Decimal("12.50") and u.resources_distributed == 9


def test_history_is_append_only_newest_first(db, populated, make_user):
    mgr, svc = make_user(Role.NGO_MANAGER), ImpactService(db)
    first = svc.submit(mgr, ImpactUpdateCreate(project_id=populated.id, notes="one"))
    second = svc.submit(mgr, ImpactUpdateCreate(project_id=populated.id, notes="two"))
    items, total = svc.history(PaginationParams(), populated.id)
    assert total == 2 and [i.id for i in items] == [second.id, first.id]


def test_unknown_project(db, make_user):
    with pytest.raises(NotFoundError):
        ImpactService(db).submit(make_user(Role.NGO_MANAGER), ImpactUpdateCreate(project_id=404))
