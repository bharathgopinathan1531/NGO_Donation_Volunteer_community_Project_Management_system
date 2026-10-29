from datetime import timedelta

import pytest

from app.core.exceptions import BusinessRuleError, ConflictError, ForbiddenError
from app.schemas.expense import ExpenseApprove, ExpenseCreate
from app.services.expense_service import ExpenseService
from app.utils.enums import ExpenseCategory, ExpenseStatus, ProjectStatus, Role
from tests.unit.factories import TODAY, mk_project


def ec(project, amount="400.00", ref="BILL-1", **kw):
    return ExpenseCreate(
        project_id=project.id, category=ExpenseCategory.MATERIALS, amount=amount, expense_date=TODAY - timedelta(days=1),
        description="Cement bags", receipt_reference=ref, **kw,
    )


@pytest.fixture()
def setup(db, make_user):
    return make_user(Role.NGO_MANAGER), make_user(Role.FINANCE_OFFICER), make_user(Role.SUPER_ADMIN), mk_project(db, budget="1000.00")


def test_submit_notifies_finance(db, setup, make_user):
    manager, finance, _, p = setup
    e = ExpenseService(db).submit(manager, ec(p))
    assert e.status == ExpenseStatus.SUBMITTED and e.submitted_by == manager.id
    from app.repositories.notification_repository import NotificationRepository
    from app.utils.pagination import PaginationParams

    _, total = NotificationRepository(db).list_for_user(finance.id, PaginationParams())
    assert total == 1


def test_proof_of_payment_required():
    with pytest.raises(ValueError):
        ExpenseCreate(project_id=1, category=ExpenseCategory.OTHER, amount="5", expense_date=TODAY, description="no proof")


def test_amount_and_attachment_url_validation():
    with pytest.raises(ValueError):
        ExpenseCreate(project_id=1, category=ExpenseCategory.OTHER, amount="-1", expense_date=TODAY, description="bad", receipt_reference="r")
    with pytest.raises(ValueError):
        ExpenseCreate(project_id=1, category=ExpenseCategory.OTHER, amount="1", expense_date=TODAY, description="bad", attachment_url="ftp://x")


def test_cannot_spend_on_planning_project_or_in_the_future(db, setup):
    manager, _, _, _ = setup
    planning = mk_project(db, name="P", status=ProjectStatus.PLANNING)
    with pytest.raises(BusinessRuleError):
        ExpenseService(db).submit(manager, ec(planning))
    future = ec(mk_project(db, name="Q")).model_copy(update={"expense_date": TODAY + timedelta(days=2)})
    with pytest.raises(BusinessRuleError):
        ExpenseService(db).submit(manager, future)


def test_duplicate_expense_detected(db, setup):
    manager, _, _, p = setup
    svc = ExpenseService(db)
    svc.submit(manager, ec(p))
    with pytest.raises(ConflictError):
        svc.submit(manager, ec(p))
    svc.submit(manager, ec(p, ref="BILL-2"))  # different receipt is fine


def test_finance_approves_within_budget(db, setup):
    manager, finance, _, p = setup
    svc = ExpenseService(db)
    e = svc.approve(finance, svc.submit(manager, ec(p, "900.00")).id, ExpenseApprove(comment="ok"))
    assert e.status == ExpenseStatus.APPROVED and e.reviewed_by == finance.id and e.reviewed_at and e.review_comment == "ok"


def test_budget_overrun_blocks_approval_and_leaves_expense_pending(db, setup):
    manager, finance, _, p = setup
    svc = ExpenseService(db)
    svc.approve(finance, svc.submit(manager, ec(p, "800.00")).id, ExpenseApprove())
    second = svc.submit(manager, ec(p, "300.00", ref="BILL-2"))
    with pytest.raises(BusinessRuleError) as exc:
        svc.approve(finance, second.id, ExpenseApprove())
    assert "exceed the project budget" in exc.value.detail
    assert second.status == ExpenseStatus.SUBMITTED


def test_project_without_budget_cannot_have_expenses_approved(db, setup):
    manager, finance, _, _ = setup
    free = mk_project(db, name="NoBudget", budget="0")
    svc = ExpenseService(db)
    e = svc.submit(manager, ec(free, "10.00"))
    with pytest.raises(BusinessRuleError):
        svc.approve(finance, e.id, ExpenseApprove())


def test_only_super_admin_can_override_the_budget(db, setup):
    manager, finance, admin, p = setup
    svc = ExpenseService(db)
    big = svc.submit(manager, ec(p, "1500.00"))
    with pytest.raises(ForbiddenError):
        svc.approve(finance, big.id, ExpenseApprove(override_budget=True))
    svc.approve(admin, big.id, ExpenseApprove(override_budget=True))
    assert big.status == ExpenseStatus.APPROVED
    from app.repositories.notification_repository import NotificationRepository
    from app.utils.pagination import PaginationParams

    notes, _ = NotificationRepository(db).list_for_user(admin.id, PaginationParams())
    assert any(n.type.value == "budget_overrun" for n in notes)


def test_submitter_cannot_approve_own_expense(db, make_user, setup):
    _, _, _, p = setup
    finance2 = make_user(Role.FINANCE_OFFICER, "fin2@example.org")
    svc = ExpenseService(db)
    e = svc.submit(finance2, ec(p))
    with pytest.raises(ForbiddenError):
        svc.approve(finance2, e.id, ExpenseApprove())


def test_state_machine(db, setup):
    manager, finance, _, p = setup
    svc = ExpenseService(db)
    e = svc.submit(manager, ec(p))
    with pytest.raises(BusinessRuleError):
        svc.reimburse(finance, e.id)  # must be approved first
    svc.reject(finance, e.id, "illegible receipt")
    assert e.status == ExpenseStatus.REJECTED
    with pytest.raises(BusinessRuleError):
        svc.approve(finance, e.id, ExpenseApprove())  # rejected is terminal
    ok = svc.submit(manager, ec(p, ref="BILL-9"))
    svc.approve(finance, ok.id, ExpenseApprove())
    assert svc.reimburse(finance, ok.id).status == ExpenseStatus.REIMBURSED
    with pytest.raises(BusinessRuleError):
        svc.reject(finance, ok.id, "too late")


def test_reviewed_expense_cannot_be_edited(db, setup):
    from app.schemas.expense import ExpenseUpdate

    manager, finance, _, p = setup
    svc = ExpenseService(db)
    e = svc.submit(manager, ec(p))
    assert svc.update(manager, e.id, ExpenseUpdate(description="Updated description")).description == "Updated description"
    svc.approve(finance, e.id, ExpenseApprove())
    with pytest.raises(BusinessRuleError):
        svc.update(manager, e.id, ExpenseUpdate(amount="1.00"))
