from sqlalchemy.orm import Session

from app.repositories.report_repository import ReportRepository
from app.schemas.dashboard import (
    BeneficiaryMetrics, CampaignGoal, CampaignMetrics, DashboardOverview, DonationMetrics, ExpenseMetrics, ProjectMetrics,
    ResourceMetrics, StockLevel, VolunteerMetrics,
)
from app.utils.money import money, pct


class DashboardService:
    """Every figure is computed from database records at request time."""

    def __init__(self, db: Session):
        self.repo = ReportRepository(db)

    def donations(self) -> DonationMetrics:
        return DonationMetrics(**self.repo.donation_totals())

    def campaigns(self) -> CampaignMetrics:
        active = self.repo.active_campaigns()
        goal = sum((money(c.goal_amount) for c in active), money(0))
        raised = sum((money(c.raised_amount) for c in active), money(0))
        return CampaignMetrics(
            active_campaigns=len(active), overall_goal_amount=goal, overall_raised_amount=raised,
            overall_achievement_pct=pct(raised, goal),
            campaigns=[
                CampaignGoal(
                    campaign_id=c.id, title=c.title, goal_amount=c.goal_amount, raised_amount=c.raised_amount,
                    achievement_pct=pct(c.raised_amount, c.goal_amount),
                )
                for c in active
            ],
        )

    def volunteers(self) -> VolunteerMetrics:
        total, active = self.repo.volunteer_counts()
        return VolunteerMetrics(total_volunteers=total, active_volunteers=active, total_volunteer_hours=self.repo.total_volunteer_hours())

    def projects(self) -> ProjectMetrics:
        counts = self.repo.project_counts()
        budget, spent = self.repo.project_budget_and_spend()
        return ProjectMetrics(**counts, total_budget=budget, total_spent=spent, budget_utilization_pct=pct(spent, budget))

    def expenses(self) -> ExpenseMetrics:
        count, amount = self.repo.pending_expenses()
        return ExpenseMetrics(pending_expense_approvals=count, pending_expense_amount=amount)

    def resources(self) -> ResourceMetrics:
        rows = self.repo.stock_levels()
        levels = [
            StockLevel(
                resource_id=r.id, name=r.name, category=r.category.value, quantity=r.quantity,
                low_stock_threshold=r.low_stock_threshold, is_low_stock=r.quantity <= r.low_stock_threshold,
            )
            for r in rows
        ]
        return ResourceMetrics(
            total_resources=len(levels), low_stock_count=sum(1 for lv in levels if lv.is_low_stock),
            total_units_in_stock=sum(lv.quantity for lv in levels), stock_levels=levels,
        )

    def beneficiaries(self) -> BeneficiaryMetrics:
        registered, served = self.repo.beneficiary_counts()
        return BeneficiaryMetrics(total_beneficiaries_registered=registered, total_beneficiaries_served=served)

    def overview(self) -> DashboardOverview:
        return DashboardOverview(
            donations=self.donations(), campaigns=self.campaigns(), volunteers=self.volunteers(), projects=self.projects(),
            expenses=self.expenses(), resources=self.resources(), beneficiaries=self.beneficiaries(),
        )
