from datetime import timedelta
from decimal import Decimal

import pytest

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models.expense import Expense
from app.schemas.budget import BudgetSet
from app.services.budget_service import BudgetService
from app.utils.enums import BudgetScope, ExpenseCategory, ExpenseStatus, Role
from app.utils.money import money, pct
from tests.unit.factories import TODAY, mk_campaign, mk_project


def spend(db, project, amount, status=ExpenseStatus.APPROVED, ref="r"):
    db.add(Expense(project_id=project.id, category=ExpenseCategory.OTHER, amount=Decimal(amount), expense_date=TODAY, description="d", receipt_reference=ref, status=status))
    db.commit()


def test_money_helpers_round_half_up_and_guard_zero():
    assert money("10.005") == Decimal("10.01") and money(None) == Decimal("0.00")
    assert pct(1, 3) == 33.33 and pct(5, 0) == 0.0


def test_utilization_counts_only_approved_and_reimbursed(db):
    p = mk_project(db, budget="1000.00")
    spend(db, p, "250.00", ExpenseStatus.APPROVED, "a")
    spend(db, p, "100.00", ExpenseStatus.REIMBURSED, "b")
    spend(db, p, "75.00", ExpenseStatus.SUBMITTED, "c")
    spend(db, p, "999.00", ExpenseStatus.REJECTED, "d")
    u = BudgetService(db).project_utilization(p.id)
    assert (u.budget, u.spent, u.pending, u.remaining) == (Decimal("1000.00"), Decimal("350.00"), Decimal("75.00"), Decimal("650.00"))
    assert u.utilization_pct == 35.0 and not u.is_overrun and u.overrun_amount == 0


def test_overrun_is_detected(db):
    p = mk_project(db, budget="100.00")
    spend(db, p, "130.50")
    u = BudgetService(db).project_utilization(p.id)
    assert u.is_overrun and u.overrun_amount == Decimal("30.50") and u.remaining == Decimal("-30.50")
    assert [x.entity_id for x in BudgetService(db).list_utilization(only_overruns=True)] == [p.id]


def test_decimal_arithmetic_has_no_float_drift(db):
    p = mk_project(db, budget="1.00")
    for i in range(3):
        spend(db, p, "0.10", ref=f"r{i}")
    assert BudgetService(db).project_utilization(p.id).spent == Decimal("0.30")


def test_set_project_budget_updates_project_and_creates_record(db, make_user):
    admin, p = make_user(Role.SUPER_ADMIN), mk_project(db, budget="0")
    svc = BudgetService(db)
    b = svc.set_budget(admin, BudgetSet(scope=BudgetScope.PROJECT, project_id=p.id, amount="2500.00"))
    assert b.amount == Decimal("2500.00") and p.budget == Decimal("2500.00")
    svc.set_budget(admin, BudgetSet(scope=BudgetScope.PROJECT, project_id=p.id, amount="3000.00"))  # replace, not duplicate
    assert BudgetService(db).repo.for_project(p.id).amount == Decimal("3000.00") and p.budget == Decimal("3000.00")


def test_budget_cannot_be_set_below_amount_already_spent(db, make_user):
    admin, p = make_user(Role.SUPER_ADMIN), mk_project(db, budget="1000.00")
    spend(db, p, "600.00")
    with pytest.raises(BusinessRuleError):
        BudgetService(db).set_budget(admin, BudgetSet(scope=BudgetScope.PROJECT, project_id=p.id, amount="500.00"))


def test_budget_scope_validation():
    with pytest.raises(ValueError):
        BudgetSet(scope=BudgetScope.PROJECT, campaign_id=1, amount="10")
    with pytest.raises(ValueError):
        BudgetSet(scope=BudgetScope.CAMPAIGN, project_id=1, amount="10")
    with pytest.raises(ValueError):
        BudgetSet(scope=BudgetScope.CAMPAIGN, campaign_id=1, project_id=1, amount="10")


def test_campaign_budget_aggregates_spend_of_its_projects(db, make_user):
    admin, c = make_user(Role.SUPER_ADMIN), mk_campaign(db)
    p1, p2 = mk_project(db, name="A", campaign_id=c.id, budget="500"), mk_project(db, name="B", campaign_id=c.id, budget="500")
    other = mk_project(db, name="Other", budget="500")
    spend(db, p1, "200.00", ref="1")
    spend(db, p2, "150.00", ref="2")
    spend(db, other, "999.00", ref="3")
    svc = BudgetService(db)
    svc.set_budget(admin, BudgetSet(scope=BudgetScope.CAMPAIGN, campaign_id=c.id, amount="1000.00"))
    u = svc.campaign_utilization(c.id)
    assert u.spent == Decimal("350.00") and u.remaining == Decimal("650.00")


def test_campaign_budget_limits_project_expense_approval(db, make_user):
    admin, c = make_user(Role.SUPER_ADMIN), mk_campaign(db)
    p = mk_project(db, campaign_id=c.id, budget="5000")
    svc = BudgetService(db)
    svc.set_budget(admin, BudgetSet(scope=BudgetScope.CAMPAIGN, campaign_id=c.id, amount="1000.00"))
    spend(db, p, "900.00")
    ok, reason = svc.check_can_spend(p, Decimal("200"))
    assert not ok and "campaign budget" in reason
    assert svc.check_can_spend(p, Decimal("100"))[0]


def test_missing_entities(db):
    svc = BudgetService(db)
    with pytest.raises(NotFoundError):
        svc.project_utilization(999)
    with pytest.raises(NotFoundError):
        svc.campaign_utilization(mk_campaign(db).id)  # no budget defined
