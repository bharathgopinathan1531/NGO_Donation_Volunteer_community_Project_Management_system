"""Status-transition tables and other business constants."""
from app.utils.enums import (
    AssignmentStatus,
    CampaignStatus,
    DonationStatus,
    ExpenseStatus,
    MilestoneStatus,
    ProjectStatus,
    VolunteerStatus,
)

CAMPAIGN_TRANSITIONS: dict[CampaignStatus, set[CampaignStatus]] = {
    CampaignStatus.DRAFT: {CampaignStatus.ACTIVE, CampaignStatus.CANCELLED},
    CampaignStatus.ACTIVE: {CampaignStatus.PAUSED, CampaignStatus.COMPLETED, CampaignStatus.CANCELLED},
    CampaignStatus.PAUSED: {CampaignStatus.ACTIVE, CampaignStatus.COMPLETED, CampaignStatus.CANCELLED},
    CampaignStatus.COMPLETED: set(),
    CampaignStatus.CANCELLED: set(),
}
CLOSED_CAMPAIGN_STATUSES = {CampaignStatus.COMPLETED, CampaignStatus.CANCELLED}

DONATION_TRANSITIONS: dict[DonationStatus, set[DonationStatus]] = {
    DonationStatus.PENDING: {DonationStatus.CONFIRMED, DonationStatus.CANCELLED},
    DonationStatus.CONFIRMED: {DonationStatus.REVERSED, DonationStatus.REFUNDED},
    DonationStatus.CANCELLED: set(),
    DonationStatus.REVERSED: set(),
    DonationStatus.REFUNDED: set(),
}

PROJECT_TRANSITIONS: dict[ProjectStatus, set[ProjectStatus]] = {
    ProjectStatus.PLANNING: {ProjectStatus.CANCELLED},  # PLANNING -> APPROVED only via the approval workflow
    ProjectStatus.APPROVED: {ProjectStatus.ACTIVE, ProjectStatus.CANCELLED},
    ProjectStatus.ACTIVE: {ProjectStatus.ON_HOLD, ProjectStatus.COMPLETED, ProjectStatus.CANCELLED},
    ProjectStatus.ON_HOLD: {ProjectStatus.ACTIVE, ProjectStatus.CANCELLED},
    ProjectStatus.COMPLETED: set(),
    ProjectStatus.CANCELLED: set(),
}
PROJECT_CLOSED_STATUSES = {ProjectStatus.COMPLETED, ProjectStatus.CANCELLED}

ASSIGNMENT_TRANSITIONS: dict[AssignmentStatus, set[AssignmentStatus]] = {
    AssignmentStatus.ASSIGNED: {AssignmentStatus.ACTIVE, AssignmentStatus.CANCELLED},
    AssignmentStatus.ACTIVE: {AssignmentStatus.COMPLETED, AssignmentStatus.CANCELLED},
    AssignmentStatus.COMPLETED: set(),
    AssignmentStatus.CANCELLED: set(),
}
LIVE_ASSIGNMENT_STATUSES = {AssignmentStatus.ASSIGNED, AssignmentStatus.ACTIVE}

EXPENSE_TRANSITIONS: dict[ExpenseStatus, set[ExpenseStatus]] = {
    ExpenseStatus.SUBMITTED: {ExpenseStatus.APPROVED, ExpenseStatus.REJECTED},
    ExpenseStatus.APPROVED: {ExpenseStatus.REIMBURSED},
    ExpenseStatus.REJECTED: set(),
    ExpenseStatus.REIMBURSED: set(),
}
SPENT_EXPENSE_STATUSES = (ExpenseStatus.APPROVED, ExpenseStatus.REIMBURSED)

MILESTONE_MANUAL_TRANSITIONS: dict[MilestoneStatus, set[MilestoneStatus]] = {
    MilestoneStatus.PENDING: {MilestoneStatus.IN_PROGRESS, MilestoneStatus.COMPLETED},
    MilestoneStatus.IN_PROGRESS: {MilestoneStatus.PENDING, MilestoneStatus.COMPLETED},
    MilestoneStatus.COMPLETED: {MilestoneStatus.IN_PROGRESS},
}

VOLUNTEER_ASSIGNABLE_STATUSES = {VolunteerStatus.ACTIVE}


def assert_transition(table: dict, current, target, label: str):
    from app.core.exceptions import BusinessRuleError

    if target == current:
        raise BusinessRuleError(f"{label} is already '{current.value}'")
    if target not in table.get(current, set()):
        allowed = ", ".join(s.value for s in table.get(current, set())) or "none"
        raise BusinessRuleError(
            f"Invalid {label} transition: '{current.value}' -> '{target.value}'. Allowed from '{current.value}': {allowed}"
        )
