from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.db.session import transaction
from app.models.budget import Budget
from app.models.campaign import Campaign
from app.models.project import Project
from app.models.user import User
from app.repositories.budget_repository import BudgetRepository
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.expense_repository import ExpenseRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.budget import BudgetSet, BudgetUtilization
from app.services.audit_service import AuditService
from app.utils.enums import BudgetScope, ExpenseStatus, ProjectStatus
from app.utils.money import money, pct
from app.utils.pagination import PaginationParams


def build_utilization(scope: BudgetScope, entity_id: int, name: str, budget: Decimal, spent: Decimal, pending: Decimal) -> BudgetUtilization:
    budget, spent, pending = money(budget), money(spent), money(pending)
    overrun = max(spent - budget, money(0))
    return BudgetUtilization(
        scope=scope, entity_id=entity_id, entity_name=name, budget=budget, spent=spent, pending=pending,
        remaining=budget - spent, utilization_pct=pct(spent, budget), is_overrun=spent > budget, overrun_amount=overrun,
    )


class BudgetService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = BudgetRepository(db)
        self.expenses = ExpenseRepository(db)
        self.projects = ProjectRepository(db)
        self.campaigns = CampaignRepository(db)
        self.audit = AuditService(db)

    # ------------------------------------------------------------------ set budgets
    def set_budget(self, actor: User, data: BudgetSet) -> Budget:
        amount = money(data.amount)
        with transaction(self.db):
            if data.scope == BudgetScope.PROJECT:
                project = self.projects.get(data.project_id, for_update=True)
                if not project:
                    raise NotFoundError("Project not found")
                if project.status == ProjectStatus.CANCELLED:
                    raise BusinessRuleError("A cancelled project cannot be budgeted")
                spent = self.expenses.spent_for_project(project.id)
                if amount < spent:
                    raise BusinessRuleError(f"Budget cannot be lower than approved expenses already spent ({spent})")
                budget = self.repo.for_project(project.id)
                project.budget = amount  # Project.budget mirrors the budget record (single source of truth for checks)
                target, entity = {"project_id": project.id}, ("project", project.id)
            else:
                campaign = self.campaigns.get(data.campaign_id)
                if not campaign:
                    raise NotFoundError("Campaign not found")
                spent = self.expenses.spent_for_campaign(campaign.id)
                if amount < spent:
                    raise BusinessRuleError(f"Budget cannot be lower than approved expenses already spent ({spent})")
                budget = self.repo.for_campaign(campaign.id)
                target, entity = {"campaign_id": campaign.id}, ("campaign", campaign.id)
            previous = budget.amount if budget else None
            if budget:
                budget.amount, budget.notes = amount, data.notes
            else:
                budget = self.repo.add(Budget(**target, amount=amount, notes=data.notes, created_by=actor.id))
            self.audit.log(actor, "budget.set", entity[0], entity[1], {"scope": data.scope, "from": previous, "to": amount})
        return budget

    def list_budgets(self, params: PaginationParams, scope: BudgetScope | None):
        return self.repo.list_budgets(params, scope=scope)

    # ------------------------------------------------------------------ utilisation
    def project_utilization(self, project_id: int) -> BudgetUtilization:
        p = self.projects.get(project_id)
        if not p:
            raise NotFoundError("Project not found")
        return self._project_util(p)

    def _project_util(self, p: Project) -> BudgetUtilization:
        return build_utilization(
            BudgetScope.PROJECT, p.id, p.name, p.budget,
            self.expenses.spent_for_project(p.id), self.expenses.sum_for_project(p.id, (ExpenseStatus.SUBMITTED,)),
        )

    def campaign_utilization(self, campaign_id: int) -> BudgetUtilization:
        c = self.campaigns.get(campaign_id)
        if not c:
            raise NotFoundError("Campaign not found")
        b = self.repo.for_campaign(c.id)
        if not b:
            raise NotFoundError("No budget has been defined for this campaign")
        return self._campaign_util(c, b.amount)

    def _campaign_util(self, c: Campaign, amount: Decimal) -> BudgetUtilization:
        return build_utilization(
            BudgetScope.CAMPAIGN, c.id, c.title, amount, self.expenses.spent_for_campaign(c.id), self.expenses.pending_for_campaign(c.id)
        )

    def list_utilization(self, scope: BudgetScope | None = None, only_overruns: bool = False) -> list[BudgetUtilization]:
        rows: list[BudgetUtilization] = []
        if scope in (None, BudgetScope.PROJECT):
            stmt = select(Project).where(Project.budget > 0, Project.status != ProjectStatus.CANCELLED).order_by(Project.id)
            rows += [self._project_util(p) for p in self.db.scalars(stmt).all()]
        if scope in (None, BudgetScope.CAMPAIGN):
            for b in self.repo.all_campaign_budgets():
                rows.append(self._campaign_util(self.campaigns.get(b.campaign_id), b.amount))
        return [r for r in rows if r.is_overrun] if only_overruns else rows

    # ------------------------------------------------------------------ rule used by expense approval
    def check_can_spend(self, project: Project, amount: Decimal) -> tuple[bool, str | None]:
        """Would approving `amount` for this project keep it within project AND campaign budgets?"""
        amount = money(amount)
        budget = money(project.budget)
        spent = self.expenses.spent_for_project(project.id)
        if budget <= 0:
            return False, "The project has no budget; set a project budget before approving expenses"
        if spent + amount > budget:
            return False, f"Approving {amount} would exceed the project budget (budget {budget}, spent {spent}, remaining {budget - spent})"
        if project.campaign_id:
            cb = self.repo.for_campaign(project.campaign_id)
            if cb:
                c_spent = self.expenses.spent_for_campaign(project.campaign_id)
                if c_spent + amount > money(cb.amount):
                    return False, f"Approving {amount} would exceed the campaign budget (budget {money(cb.amount)}, spent {c_spent})"
        return True, None
