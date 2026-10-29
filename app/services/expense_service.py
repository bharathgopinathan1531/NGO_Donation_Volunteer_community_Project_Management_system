from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import EXPENSE_TRANSITIONS, assert_transition
from app.core.exceptions import BusinessRuleError, ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import Permission, has_permission
from app.db.session import transaction
from app.models.expense import Expense
from app.models.user import User
from app.repositories.expense_repository import ExpenseRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.expense import ExpenseApprove, ExpenseCreate, ExpenseUpdate
from app.services.audit_service import AuditService, diff, snapshot
from app.services.budget_service import BudgetService
from app.services.notification_service import NotificationService
from app.utils.date_utils import today, utcnow
from app.utils.enums import ExpenseCategory, ExpenseStatus, NotificationType, ProjectStatus, Role
from app.utils.money import money
from app.utils.pagination import PaginationParams
from app.utils.sorting import SortParams

AUDIT_FIELDS = ["project_id", "category", "amount", "expense_date", "description", "receipt_reference", "attachment_url", "status"]
SPENDABLE_PROJECT_STATUSES = {ProjectStatus.APPROVED, ProjectStatus.ACTIVE, ProjectStatus.ON_HOLD}


class ExpenseService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ExpenseRepository(db)
        self.projects = ProjectRepository(db)
        self.budgets = BudgetService(db)
        self.audit = AuditService(db)
        self.notifications = NotificationService(db)

    def get(self, actor: User, expense_id: int) -> Expense:
        e = self.repo.get(expense_id)
        if not e:
            raise NotFoundError("Expense not found")
        if has_permission(actor.role, Permission.EXPENSES_READ) or e.submitted_by == actor.id:
            return e
        raise ForbiddenError("You do not have access to this expense")

    # ------------------------------------------------------------------ commands
    def submit(self, actor: User, data: ExpenseCreate) -> Expense:
        if data.expense_date > today():
            raise BusinessRuleError("Expense date cannot be in the future")
        with transaction(self.db):
            p = self.projects.get(data.project_id)
            if not p:
                raise NotFoundError("Project not found")
            if p.status not in SPENDABLE_PROJECT_STATUSES:
                raise BusinessRuleError(f"Expenses can only be recorded for approved or active projects (this one is '{p.status.value}')")
            if data.receipt_reference:
                dup = self.db.scalar(
                    select(Expense.id).where(
                        Expense.project_id == p.id, Expense.receipt_reference == data.receipt_reference,
                        Expense.amount == money(data.amount), Expense.expense_date == data.expense_date,
                        Expense.status != ExpenseStatus.REJECTED,
                    )
                )
                if dup:
                    raise ConflictError(f"This expense looks like a duplicate of expense #{dup}")
            e = self.repo.add(
                Expense(**data.model_dump(exclude={"amount"}), amount=money(data.amount), status=ExpenseStatus.SUBMITTED, submitted_by=actor.id)
            )
            self.notifications.notify_roles(
                {Role.FINANCE_OFFICER, Role.SUPER_ADMIN}, NotificationType.EXPENSE_PENDING, "Expense awaiting approval",
                f"Expense #{e.id} of {e.amount} for project '{p.name}' is pending review.",
                exclude_user_id=actor.id, entity="expense", entity_id=e.id, dedupe_key=f"expense_pending:{e.id}",
            )
            self.audit.log(actor, "expense.submitted", "expense", e.id, snapshot(e, AUDIT_FIELDS))
        return e

    def update(self, actor: User, expense_id: int, data: ExpenseUpdate) -> Expense:
        changes = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
        with transaction(self.db):
            e = self.repo.get(expense_id, for_update=True)
            if not e:
                raise NotFoundError("Expense not found")
            if e.submitted_by != actor.id and actor.role not in (Role.SUPER_ADMIN, Role.NGO_MANAGER):
                raise ForbiddenError("Only the submitter can edit this expense")
            if e.status != ExpenseStatus.SUBMITTED:
                raise BusinessRuleError(f"A {e.status.value} expense can no longer be edited")
            if "expense_date" in changes and changes["expense_date"] > today():
                raise BusinessRuleError("Expense date cannot be in the future")
            before = snapshot(e, AUDIT_FIELDS)
            for k, v in changes.items():
                setattr(e, k, money(v) if k == "amount" else v)
            if not e.receipt_reference and not e.attachment_url:
                raise BusinessRuleError("An expense needs a receipt reference or an attachment URL")
            self.audit.log(actor, "expense.updated", "expense", e.id, diff(before, snapshot(e, AUDIT_FIELDS)))
        return e

    def approve(self, actor: User, expense_id: int, data: ExpenseApprove) -> Expense:
        with transaction(self.db):
            e = self.repo.get(expense_id, for_update=True)
            if not e:
                raise NotFoundError("Expense not found")
            assert_transition(EXPENSE_TRANSITIONS, e.status, ExpenseStatus.APPROVED, "expense status")
            if e.submitted_by == actor.id and actor.role != Role.SUPER_ADMIN:
                raise ForbiddenError("You cannot approve an expense that you submitted")
            project = self.projects.get(e.project_id, for_update=True)
            ok, reason = self.budgets.check_can_spend(project, e.amount)
            overridden = False
            if not ok:
                if data.override_budget:
                    if actor.role != Role.SUPER_ADMIN:
                        raise ForbiddenError("Only a super admin can override budget limits")
                    overridden = True
                else:
                    raise BusinessRuleError(reason, extra={"hint": "A super admin may approve with override_budget=true"})
            e.status, e.reviewed_by, e.reviewed_at, e.review_comment = ExpenseStatus.APPROVED, actor.id, utcnow(), data.comment
            self.db.flush()
            self.notifications.notify(
                [e.submitted_by], NotificationType.EXPENSE_PENDING, "Expense approved",
                f"Your expense #{e.id} of {e.amount} was approved.", entity="expense", entity_id=e.id, dedupe_key=f"expense_approved:{e.id}",
            )
            util = self.budgets.project_utilization(project.id)
            if util.is_overrun:
                self.notifications.notify(
                    self.notifications.privileged_ids(), NotificationType.BUDGET_OVERRUN, "Budget overrun",
                    f"Project '{project.name}' has spent {util.spent} against a budget of {util.budget}.",
                    entity="project", entity_id=project.id, dedupe_key=f"budget_overrun:project:{project.id}",
                )
            self.audit.log(
                actor, "expense.approved", "expense", e.id,
                {"amount": e.amount, "project_id": project.id, "comment": data.comment, "budget_overridden": overridden,
                 "project_spent_after": util.spent, "project_budget": util.budget},
            )
        return e

    def reject(self, actor: User, expense_id: int, comment: str) -> Expense:
        with transaction(self.db):
            e = self.repo.get(expense_id, for_update=True)
            if not e:
                raise NotFoundError("Expense not found")
            assert_transition(EXPENSE_TRANSITIONS, e.status, ExpenseStatus.REJECTED, "expense status")
            if e.submitted_by == actor.id and actor.role != Role.SUPER_ADMIN:
                raise ForbiddenError("You cannot review an expense that you submitted")
            e.status, e.reviewed_by, e.reviewed_at, e.review_comment = ExpenseStatus.REJECTED, actor.id, utcnow(), comment
            self.notifications.notify(
                [e.submitted_by], NotificationType.EXPENSE_PENDING, "Expense rejected",
                f"Your expense #{e.id} was rejected: {comment}", entity="expense", entity_id=e.id, dedupe_key=f"expense_rejected:{e.id}",
            )
            self.audit.log(actor, "expense.rejected", "expense", e.id, {"comment": comment, "amount": e.amount})
        return e

    def reimburse(self, actor: User, expense_id: int) -> Expense:
        with transaction(self.db):
            e = self.repo.get(expense_id, for_update=True)
            if not e:
                raise NotFoundError("Expense not found")
            assert_transition(EXPENSE_TRANSITIONS, e.status, ExpenseStatus.REIMBURSED, "expense status")
            e.status = ExpenseStatus.REIMBURSED
            self.audit.log(actor, "expense.reimbursed", "expense", e.id, {"amount": e.amount})
        return e

    # ------------------------------------------------------------------ queries
    def list_expenses(
        self, actor: User, params: PaginationParams, sort: SortParams, *, project_id: int | None, status: ExpenseStatus | None,
        category: ExpenseCategory | None, search: str | None, date_from: date | None, date_to: date | None,
    ):
        submitted_by = None
        if not has_permission(actor.role, Permission.EXPENSES_READ):
            submitted_by = actor.id
        return self.repo.list_expenses(
            params, sort, project_id=project_id, status=status, category=category, submitted_by=submitted_by, search=search,
            date_from=date_from, date_to=date_to,
        )
