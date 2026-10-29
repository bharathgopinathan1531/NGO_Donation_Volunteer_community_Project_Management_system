from datetime import timedelta
from decimal import Decimal

from app.models.beneficiary_assistance import BeneficiaryAssistance
from app.models.expense import Expense
from app.services.approval_service import ApprovalService
from app.services.dashboard_service import DashboardService
from app.utils.enums import CampaignStatus, DonationStatus, ExpenseCategory, ExpenseStatus, ProjectStatus, Role, VolunteerStatus
from tests.unit.factories import (
    TODAY, mk_beneficiary, mk_campaign, mk_donation, mk_donor, mk_project, mk_resource, mk_volunteer,
)


def test_empty_database_yields_zeros_not_errors(db):
    o = DashboardService(db).overview()
    assert o.donations.total_donations_count == 0 and o.donations.confirmed_donations_amount == 0
    assert o.campaigns.active_campaigns == 0 and o.campaigns.overall_achievement_pct == 0
    assert o.projects.budget_utilization_pct == 0 and o.resources.stock_levels == []


def test_donation_metrics_separate_total_from_confirmed(db):
    donor, campaign = mk_donor(db), mk_campaign(db)
    mk_donation(db, donor, campaign, "100.00", ref="a")
    mk_donation(db, donor, campaign, "50.00", ref="b")
    mk_donation(db, donor, campaign, "25.00", DonationStatus.PENDING, ref="c")
    mk_donation(db, donor, campaign, "10.00", DonationStatus.REFUNDED, ref="d")
    m = DashboardService(db).donations()
    assert (m.total_donations_count, m.total_donations_amount) == (4, Decimal("185.00"))
    assert (m.confirmed_donations_count, m.confirmed_donations_amount) == (2, Decimal("150.00"))


def test_campaign_goal_achievement_only_for_active_campaigns(db):
    mk_campaign(db, title="A", goal="1000.00", raised="250.00")
    mk_campaign(db, title="B", goal="3000.00", raised="750.00")
    mk_campaign(db, title="Closed", status=CampaignStatus.COMPLETED, goal="500.00", raised="500.00")
    m = DashboardService(db).campaigns()
    assert m.active_campaigns == 2 and m.overall_goal_amount == Decimal("4000.00") and m.overall_raised_amount == Decimal("1000.00")
    assert m.overall_achievement_pct == 25.0 and [c.achievement_pct for c in m.campaigns] == [25.0, 25.0]


def test_volunteer_and_beneficiary_counts(db):
    mk_volunteer(db, "a@example.org")
    mk_volunteer(db, "b@example.org", status=VolunteerStatus.INACTIVE)
    p, res = mk_project(db), mk_resource(db)
    served, _unserved = mk_beneficiary(db, "S"), mk_beneficiary(db, "U")
    db.add(BeneficiaryAssistance(beneficiary_id=served.id, project_id=p.id, resource_id=res.id, assistance_type="x", quantity=1, distribution_date=TODAY))
    db.commit()
    s = DashboardService(db)
    assert (s.volunteers().total_volunteers, s.volunteers().active_volunteers) == (2, 1)
    assert (s.beneficiaries().total_beneficiaries_registered, s.beneficiaries().total_beneficiaries_served) == (2, 1)


def test_project_metrics_and_budget_utilization(db, make_user):
    admin = make_user(Role.SUPER_ADMIN)
    active = mk_project(db, name="Active", budget="1000.00")
    mk_project(db, name="Cancelled", status=ProjectStatus.CANCELLED, budget="9999.00")  # ignored in budget totals
    waiting = mk_project(db, name="Waiting", status=ProjectStatus.PLANNING, budget="0")
    ApprovalService(db).submit(admin, waiting.id, None)
    for amount, status, ref in (("400.00", ExpenseStatus.APPROVED, "1"), ("100.00", ExpenseStatus.SUBMITTED, "2")):
        db.add(Expense(project_id=active.id, category=ExpenseCategory.OTHER, amount=Decimal(amount), expense_date=TODAY, description="d", receipt_reference=ref, status=status))
    db.commit()
    s = DashboardService(db)
    pm = s.projects()
    assert pm.active_projects == 1 and pm.pending_project_approvals == 1 and pm.total_projects == 3
    assert pm.total_budget == Decimal("1000.00") and pm.total_spent == Decimal("400.00") and pm.budget_utilization_pct == 40.0
    em = s.expenses()
    assert em.pending_expense_approvals == 1 and em.pending_expense_amount == Decimal("100.00")


def test_approved_project_no_longer_counts_as_pending(db, make_user):
    admin, p = make_user(Role.SUPER_ADMIN), mk_project(db, status=ProjectStatus.PLANNING)
    svc = ApprovalService(db)
    svc.submit(admin, p.id, None)
    assert DashboardService(db).projects().pending_project_approvals == 1
    svc.approve(admin, p.id, None)
    assert DashboardService(db).projects().pending_project_approvals == 0


def test_stock_levels_flag_low_stock(db):
    mk_resource(db, "Plenty", qty=100, threshold=10)
    mk_resource(db, "Scarce", qty=3, threshold=10)
    m = DashboardService(db).resources()
    assert m.total_resources == 2 and m.low_stock_count == 1 and m.total_units_in_stock == 103
    assert {lv.name: lv.is_low_stock for lv in m.stock_levels} == {"Plenty": False, "Scarce": True}
