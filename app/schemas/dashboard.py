from decimal import Decimal

from pydantic import BaseModel


class DonationMetrics(BaseModel):
    total_donations_count: int
    total_donations_amount: Decimal
    confirmed_donations_count: int
    confirmed_donations_amount: Decimal


class CampaignGoal(BaseModel):
    campaign_id: int
    title: str
    goal_amount: Decimal
    raised_amount: Decimal
    achievement_pct: float


class CampaignMetrics(BaseModel):
    active_campaigns: int
    overall_goal_amount: Decimal  # across active campaigns
    overall_raised_amount: Decimal
    overall_achievement_pct: float
    campaigns: list[CampaignGoal]


class VolunteerMetrics(BaseModel):
    total_volunteers: int
    active_volunteers: int
    total_volunteer_hours: Decimal


class ProjectMetrics(BaseModel):
    active_projects: int
    pending_project_approvals: int
    total_projects: int
    total_budget: Decimal
    total_spent: Decimal
    budget_utilization_pct: float


class ExpenseMetrics(BaseModel):
    pending_expense_approvals: int
    pending_expense_amount: Decimal


class StockLevel(BaseModel):
    resource_id: int
    name: str
    category: str
    quantity: int
    low_stock_threshold: int
    is_low_stock: bool


class ResourceMetrics(BaseModel):
    total_resources: int
    low_stock_count: int
    total_units_in_stock: int
    stock_levels: list[StockLevel]


class BeneficiaryMetrics(BaseModel):
    total_beneficiaries_registered: int
    total_beneficiaries_served: int


class DashboardOverview(BaseModel):
    donations: DonationMetrics
    campaigns: CampaignMetrics
    volunteers: VolunteerMetrics
    projects: ProjectMetrics
    expenses: ExpenseMetrics
    resources: ResourceMetrics
    beneficiaries: BeneficiaryMetrics
