from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from app.core.constants import SPENT_EXPENSE_STATUSES
from app.models.expense import Expense
from app.models.project import Project
from app.repositories import BaseRepository
from app.utils.enums import ExpenseCategory, ExpenseStatus
from app.utils.filtering import apply_date_range, apply_equals, apply_search
from app.utils.money import money
from app.utils.pagination import PaginationParams, paginate
from app.utils.sorting import SortParams, apply_sorting


class ExpenseRepository(BaseRepository[Expense]):
    model = Expense

    def list_expenses(
        self, params: PaginationParams, sort: SortParams, *, project_id: int | None = None, status: ExpenseStatus | None = None,
        category: ExpenseCategory | None = None, submitted_by: int | None = None, search: str | None = None,
        date_from: date | None = None, date_to: date | None = None,
    ):
        stmt = apply_equals(select(Expense), Expense, project_id=project_id, status=status, category=category, submitted_by=submitted_by)
        stmt = apply_search(stmt, [Expense.description, Expense.receipt_reference], search)
        stmt = apply_date_range(stmt, Expense.expense_date, date_from, date_to)
        stmt = apply_sorting(stmt, Expense, sort, {"id", "amount", "expense_date", "status", "category", "created_at"}, default="id", default_order="desc")
        return paginate(self.db, stmt, params)

    def sum_for_project(self, project_id: int, statuses) -> Decimal:
        total = self.db.scalar(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(Expense.project_id == project_id, Expense.status.in_(statuses))
        )
        return money(total)

    def spent_for_project(self, project_id: int) -> Decimal:
        return self.sum_for_project(project_id, SPENT_EXPENSE_STATUSES)

    def spent_for_campaign(self, campaign_id: int) -> Decimal:
        total = self.db.scalar(
            select(func.coalesce(func.sum(Expense.amount), 0))
            .join(Project, Project.id == Expense.project_id)
            .where(Project.campaign_id == campaign_id, Expense.status.in_(SPENT_EXPENSE_STATUSES))
        )
        return money(total)

    def pending_for_campaign(self, campaign_id: int) -> Decimal:
        total = self.db.scalar(
            select(func.coalesce(func.sum(Expense.amount), 0))
            .join(Project, Project.id == Expense.project_id)
            .where(Project.campaign_id == campaign_id, Expense.status == ExpenseStatus.SUBMITTED)
        )
        return money(total)

    def pending(self) -> list[Expense]:
        return list(self.db.scalars(select(Expense).where(Expense.status == ExpenseStatus.SUBMITTED)).all())
