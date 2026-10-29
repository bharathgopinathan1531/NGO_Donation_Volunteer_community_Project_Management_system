from sqlalchemy import select

from app.models.budget import Budget
from app.repositories import BaseRepository
from app.utils.enums import BudgetScope
from app.utils.pagination import PaginationParams, paginate


class BudgetRepository(BaseRepository[Budget]):
    model = Budget

    def for_project(self, project_id: int) -> Budget | None:
        return self.db.scalar(select(Budget).where(Budget.project_id == project_id))

    def for_campaign(self, campaign_id: int) -> Budget | None:
        return self.db.scalar(select(Budget).where(Budget.campaign_id == campaign_id))

    def list_budgets(self, params: PaginationParams, *, scope: BudgetScope | None = None):
        stmt = select(Budget)
        if scope == BudgetScope.CAMPAIGN:
            stmt = stmt.where(Budget.campaign_id.is_not(None))
        elif scope == BudgetScope.PROJECT:
            stmt = stmt.where(Budget.project_id.is_not(None))
        return paginate(self.db, stmt.order_by(Budget.id), params)

    def all_project_budgets(self) -> list[Budget]:
        return list(self.db.scalars(select(Budget).where(Budget.project_id.is_not(None))).all())

    def all_campaign_budgets(self) -> list[Budget]:
        return list(self.db.scalars(select(Budget).where(Budget.campaign_id.is_not(None))).all())
