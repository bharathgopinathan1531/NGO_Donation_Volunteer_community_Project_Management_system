"""Reporting and dashboard aggregate queries (read-only)."""
from datetime import date
from decimal import Decimal

from sqlalchemy import Float, Select, and_, case, cast, distinct, extract, func, select
from sqlalchemy.orm import Session

from app.core.constants import SPENT_EXPENSE_STATUSES
from app.models.attendance import Attendance
from app.models.beneficiary import Beneficiary
from app.models.beneficiary_assistance import BeneficiaryAssistance
from app.models.campaign import Campaign
from app.models.donation import Donation
from app.models.donor import Donor
from app.models.expense import Expense
from app.models.milestone import Milestone
from app.models.project import Project
from app.models.project_approval import ProjectApproval
from app.models.resource import Resource
from app.models.resource_allocation import ResourceAllocation
from app.models.volunteer import Volunteer
from app.models.volunteer_assignment import VolunteerAssignment as VA
from app.utils.enums import (
    ApprovalAction, AssignmentStatus, AttendanceStatus, BeneficiaryCategory, CampaignStatus, DonationStatus, ExpenseCategory,
    ExpenseStatus, MilestoneStatus, ProjectStatus, ResourceCategory, VolunteerStatus,
)
from app.utils.filtering import apply_date_range, apply_equals
from app.utils.money import money


class ReportRepository:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------ report statements
    def donation_summary(
        self, group_by: str, *, campaign_id: int | None, status: DonationStatus | None, date_from: date | None, date_to: date | None
    ) -> Select:
        groups = {
            "campaign": [Campaign.id.label("campaign_id"), Campaign.title.label("campaign")],
            "donor": [Donor.id.label("donor_id"), Donor.name.label("donor")],
            "method": [Donation.method.label("method")],
            "status": [Donation.status.label("status")],
            "month": [extract("year", Donation.donation_date).label("year"), extract("month", Donation.donation_date).label("month")],
        }
        cols = groups[group_by]
        stmt = (
            select(
                *cols,
                func.count(Donation.id).label("donation_count"),
                func.coalesce(func.sum(Donation.amount), 0).label("total_amount"),
                func.coalesce(func.avg(Donation.amount), 0).label("average_amount"),
            )
            .select_from(Donation)
            .join(Campaign, Campaign.id == Donation.campaign_id)
            .join(Donor, Donor.id == Donation.donor_id)
            .group_by(*cols)
        )
        stmt = apply_equals(stmt, Donation, campaign_id=campaign_id, status=status)
        return apply_date_range(stmt, Donation.donation_date, date_from, date_to)

    def campaign_performance(
        self, *, campaign_id: int | None, status: CampaignStatus | None, date_from: date | None, date_to: date | None
    ) -> Select:
        d = (
            select(
                Donation.campaign_id.label("cid"),
                func.count(Donation.id).label("n"),
                func.sum(Donation.amount).label("amt"),
                func.count(distinct(Donation.donor_id)).label("donors"),
            )
            .where(Donation.status == DonationStatus.CONFIRMED)
            .group_by(Donation.campaign_id)
        )
        d = apply_date_range(d, Donation.donation_date, date_from, date_to).subquery()
        stmt = select(
            Campaign.id.label("campaign_id"),
            Campaign.title.label("title"),
            Campaign.category.label("category"),
            Campaign.status.label("status"),
            Campaign.goal_amount.label("goal_amount"),
            Campaign.raised_amount.label("raised_amount"),
            (cast(Campaign.raised_amount, Float) * 100.0 / cast(Campaign.goal_amount, Float)).label("achievement_pct"),
            func.coalesce(d.c.n, 0).label("confirmed_donations"),
            func.coalesce(d.c.amt, 0).label("confirmed_amount_in_period"),
            func.coalesce(d.c.donors, 0).label("unique_donors"),
        ).outerjoin(d, d.c.cid == Campaign.id)
        return apply_equals(stmt, Campaign, id=campaign_id, status=status)

    def volunteer_contribution(
        self, *, project_id: int | None, status: VolunteerStatus | None, date_from: date | None, date_to: date | None
    ) -> Select:
        join_cond = and_(Attendance.assignment_id == VA.id, Attendance.status == AttendanceStatus.PRESENT)
        att = select(
            VA.volunteer_id.label("vid"),
            func.count(distinct(VA.id)).label("assignments"),
            func.count(distinct(VA.project_id)).label("projects"),
            func.coalesce(func.sum(Attendance.hours), 0).label("hours"),
            func.count(distinct(Attendance.id)).label("days_present"),
        ).select_from(VA).outerjoin(Attendance, join_cond)
        att = att.where(VA.status != AssignmentStatus.CANCELLED)
        if project_id is not None:
            att = att.where(VA.project_id == project_id)
        att = apply_date_range(att, Attendance.attendance_date, date_from, date_to) if (date_from or date_to) else att
        att = att.group_by(VA.volunteer_id).subquery()
        stmt = select(
            Volunteer.id.label("volunteer_id"),
            Volunteer.full_name.label("volunteer"),
            Volunteer.status.label("status"),
            att.c.assignments.label("assignments"),
            att.c.projects.label("projects"),
            att.c.days_present.label("days_present"),
            att.c.hours.label("total_hours"),
        ).join(att, att.c.vid == Volunteer.id)
        return apply_equals(stmt, Volunteer, status=status)

    def project_progress(
        self, today: date, *, project_id: int | None, status: ProjectStatus | None, campaign_id: int | None,
        date_from: date | None, date_to: date | None,
    ) -> Select:
        m = (
            select(
                Milestone.project_id.label("pid"),
                func.count(Milestone.id).label("total"),
                func.sum(case((Milestone.status == MilestoneStatus.COMPLETED, 1), else_=0)).label("done"),
                func.sum(case((and_(Milestone.due_date < today, Milestone.status != MilestoneStatus.COMPLETED), 1), else_=0)).label("overdue"),
            )
            .group_by(Milestone.project_id)
            .subquery()
        )
        e = (
            select(Expense.project_id.label("pid"), func.sum(Expense.amount).label("spent"))
            .where(Expense.status.in_(SPENT_EXPENSE_STATUSES))
            .group_by(Expense.project_id)
            .subquery()
        )
        total = func.coalesce(m.c.total, 0)
        done = func.coalesce(m.c.done, 0)
        spent = func.coalesce(e.c.spent, 0)
        stmt = (
            select(
                Project.id.label("project_id"),
                Project.name.label("project"),
                Project.status.label("status"),
                Project.start_date.label("start_date"),
                Project.end_date.label("end_date"),
                Project.budget.label("budget"),
                spent.label("spent"),
                case((Project.budget > 0, cast(spent, Float) * 100.0 / cast(Project.budget, Float)), else_=0.0).label("budget_utilization_pct"),
                total.label("milestones_total"),
                done.label("milestones_completed"),
                case((total > 0, cast(done, Float) * 100.0 / total), else_=0.0).label("milestone_completion_pct"),
                func.coalesce(m.c.overdue, 0).label("overdue_milestones"),
            )
            .outerjoin(m, m.c.pid == Project.id)
            .outerjoin(e, e.c.pid == Project.id)
        )
        stmt = apply_equals(stmt, Project, id=project_id, status=status, campaign_id=campaign_id)
        return apply_date_range(stmt, Project.start_date, date_from, date_to)

    def expense_report(
        self, *, project_id: int | None, campaign_id: int | None, status: ExpenseStatus | None, category: ExpenseCategory | None,
        date_from: date | None, date_to: date | None,
    ) -> Select:
        stmt = (
            select(
                Expense.id.label("expense_id"),
                Expense.project_id.label("project_id"),
                Project.name.label("project"),
                Expense.category.label("category"),
                Expense.amount.label("amount"),
                Expense.expense_date.label("expense_date"),
                Expense.status.label("status"),
                Expense.receipt_reference.label("receipt_reference"),
                Expense.submitted_by.label("submitted_by"),
                Expense.reviewed_by.label("reviewed_by"),
            )
            .select_from(Expense)
            .join(Project, Project.id == Expense.project_id)
        )
        stmt = apply_equals(stmt, Expense, project_id=project_id, status=status, category=category)
        if campaign_id is not None:
            stmt = stmt.where(Project.campaign_id == campaign_id)
        return apply_date_range(stmt, Expense.expense_date, date_from, date_to)

    def resource_distribution(
        self, *, project_id: int | None, resource_id: int | None, category: ResourceCategory | None,
        date_from: date | None, date_to: date | None,
    ) -> Select:
        a = select(
            ResourceAllocation.resource_id.label("rid"), ResourceAllocation.project_id.label("pid"),
            func.sum(ResourceAllocation.quantity).label("allocated"),
        ).group_by(ResourceAllocation.resource_id, ResourceAllocation.project_id)
        a = apply_date_range(a, ResourceAllocation.allocated_at, date_from, date_to).subquery()
        d = select(
            BeneficiaryAssistance.resource_id.label("rid"), BeneficiaryAssistance.project_id.label("pid"),
            func.sum(BeneficiaryAssistance.quantity).label("distributed"),
            func.count(distinct(BeneficiaryAssistance.beneficiary_id)).label("beneficiaries"),
        ).where(BeneficiaryAssistance.resource_id.is_not(None)).group_by(BeneficiaryAssistance.resource_id, BeneficiaryAssistance.project_id)
        d = apply_date_range(d, BeneficiaryAssistance.distribution_date, date_from, date_to).subquery()
        distributed = func.coalesce(d.c.distributed, 0)
        stmt = (
            select(
                Resource.id.label("resource_id"),
                Resource.name.label("resource"),
                Resource.category.label("category"),
                Project.id.label("project_id"),
                Project.name.label("project"),
                a.c.allocated.label("allocated_quantity"),
                distributed.label("distributed_quantity"),
                (a.c.allocated - distributed).label("remaining_quantity"),
                func.coalesce(d.c.beneficiaries, 0).label("beneficiaries_reached"),
            )
            .select_from(a)
            .join(Resource, Resource.id == a.c.rid)
            .join(Project, Project.id == a.c.pid)
            .outerjoin(d, and_(d.c.rid == a.c.rid, d.c.pid == a.c.pid))
        )
        if project_id is not None:
            stmt = stmt.where(Project.id == project_id)
        if resource_id is not None:
            stmt = stmt.where(Resource.id == resource_id)
        if category is not None:
            stmt = stmt.where(Resource.category == category)
        return stmt

    def beneficiary_impact(
        self, group_by: str, *, project_id: int | None, category: BeneficiaryCategory | None, date_from: date | None, date_to: date | None
    ) -> Select:
        if group_by == "category":
            cols = [Beneficiary.category.label("category")]
        else:
            cols = [Project.id.label("project_id"), Project.name.label("project")]
        stmt = (
            select(
                *cols,
                func.count(distinct(BeneficiaryAssistance.beneficiary_id)).label("beneficiaries_served"),
                func.count(BeneficiaryAssistance.id).label("assistance_records"),
                func.coalesce(func.sum(BeneficiaryAssistance.quantity), 0).label("resources_distributed"),
            )
            .select_from(BeneficiaryAssistance)
            .join(Beneficiary, Beneficiary.id == BeneficiaryAssistance.beneficiary_id)
            .join(Project, Project.id == BeneficiaryAssistance.project_id)
            .group_by(*cols)
        )
        if project_id is not None:
            stmt = stmt.where(BeneficiaryAssistance.project_id == project_id)
        if category is not None:
            stmt = stmt.where(Beneficiary.category == category)
        return apply_date_range(stmt, BeneficiaryAssistance.distribution_date, date_from, date_to)

    # ------------------------------------------------------------------ dashboard aggregates
    def donation_totals(self) -> dict:
        total_count, total_amount = self.db.execute(select(func.count(Donation.id), func.coalesce(func.sum(Donation.amount), 0))).one()
        conf_count, conf_amount = self.db.execute(
            select(func.count(Donation.id), func.coalesce(func.sum(Donation.amount), 0)).where(Donation.status == DonationStatus.CONFIRMED)
        ).one()
        return {
            "total_donations_count": total_count, "total_donations_amount": money(total_amount),
            "confirmed_donations_count": conf_count, "confirmed_donations_amount": money(conf_amount),
        }

    def active_campaigns(self) -> list[Campaign]:
        return list(self.db.scalars(select(Campaign).where(Campaign.status == CampaignStatus.ACTIVE).order_by(Campaign.id)).all())

    def volunteer_counts(self) -> tuple[int, int]:
        total = self.db.scalar(select(func.count(Volunteer.id))) or 0
        active = self.db.scalar(select(func.count(Volunteer.id)).where(Volunteer.status == VolunteerStatus.ACTIVE)) or 0
        return total, active

    def total_volunteer_hours(self) -> Decimal:
        return money(self.db.scalar(select(func.coalesce(func.sum(Attendance.hours), 0)).where(Attendance.status == AttendanceStatus.PRESENT)))

    def project_counts(self) -> dict:
        total = self.db.scalar(select(func.count(Project.id))) or 0
        active = self.db.scalar(select(func.count(Project.id)).where(Project.status == ProjectStatus.ACTIVE)) or 0
        last = select(func.max(ProjectApproval.id)).group_by(ProjectApproval.project_id)
        pending = self.db.scalar(
            select(func.count(ProjectApproval.id)).where(ProjectApproval.id.in_(last), ProjectApproval.action == ApprovalAction.SUBMITTED)
        ) or 0
        return {"total_projects": total, "active_projects": active, "pending_project_approvals": pending}

    def project_budget_and_spend(self) -> tuple[Decimal, Decimal]:
        """Budget and spend for non-cancelled projects."""
        live = Project.status != ProjectStatus.CANCELLED
        budget = self.db.scalar(select(func.coalesce(func.sum(Project.budget), 0)).where(live))
        spent = self.db.scalar(
            select(func.coalesce(func.sum(Expense.amount), 0)).join(Project, Project.id == Expense.project_id).where(live, Expense.status.in_(SPENT_EXPENSE_STATUSES))
        )
        return money(budget), money(spent)

    def pending_expenses(self) -> tuple[int, Decimal]:
        count, amount = self.db.execute(
            select(func.count(Expense.id), func.coalesce(func.sum(Expense.amount), 0)).where(Expense.status == ExpenseStatus.SUBMITTED)
        ).one()
        return count, money(amount)

    def stock_levels(self) -> list[Resource]:
        return list(self.db.scalars(select(Resource).order_by(Resource.name)).all())

    def beneficiary_counts(self) -> tuple[int, int]:
        registered = self.db.scalar(select(func.count(Beneficiary.id))) or 0
        served = self.db.scalar(select(func.count(distinct(BeneficiaryAssistance.beneficiary_id)))) or 0
        return registered, served
