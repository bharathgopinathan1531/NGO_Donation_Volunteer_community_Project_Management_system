from decimal import Decimal

from sqlalchemy import distinct, func, select

from app.core.constants import SPENT_EXPENSE_STATUSES
from app.models.attendance import Attendance
from app.models.beneficiary_assistance import BeneficiaryAssistance
from app.models.expense import Expense
from app.models.impact_update import ImpactUpdate
from app.models.milestone import Milestone
from app.models.project import Project
from app.models.volunteer_assignment import VolunteerAssignment
from app.repositories import BaseRepository
from app.utils.enums import AttendanceStatus, MilestoneStatus, ProjectStatus
from app.utils.money import money
from app.utils.pagination import PaginationParams, paginate


class ImpactRepository(BaseRepository[ImpactUpdate]):
    model = ImpactUpdate

    def history(self, params: PaginationParams, project_id: int | None = None):
        stmt = select(ImpactUpdate)
        if project_id is not None:
            stmt = stmt.where(ImpactUpdate.project_id == project_id)
        return paginate(self.db, stmt.order_by(ImpactUpdate.id.desc()), params)

    # ---- live metrics computed from operational records (optionally for a single project) ----
    def beneficiaries_served(self, project_id: int | None = None) -> int:
        stmt = select(func.count(distinct(BeneficiaryAssistance.beneficiary_id)))
        if project_id is not None:
            stmt = stmt.where(BeneficiaryAssistance.project_id == project_id)
        return self.db.scalar(stmt) or 0

    def volunteer_hours(self, project_id: int | None = None) -> Decimal:
        stmt = (
            select(func.coalesce(func.sum(Attendance.hours), 0))
            .join(VolunteerAssignment, VolunteerAssignment.id == Attendance.assignment_id)
            .where(Attendance.status == AttendanceStatus.PRESENT)
        )
        if project_id is not None:
            stmt = stmt.where(VolunteerAssignment.project_id == project_id)
        return money(self.db.scalar(stmt))

    def resources_distributed(self, project_id: int | None = None) -> int:
        stmt = select(func.coalesce(func.sum(BeneficiaryAssistance.quantity), 0))
        if project_id is not None:
            stmt = stmt.where(BeneficiaryAssistance.project_id == project_id)
        return self.db.scalar(stmt) or 0

    def funds_utilized(self, project_id: int | None = None) -> Decimal:
        stmt = select(func.coalesce(func.sum(Expense.amount), 0)).where(Expense.status.in_(SPENT_EXPENSE_STATUSES))
        if project_id is not None:
            stmt = stmt.where(Expense.project_id == project_id)
        return money(self.db.scalar(stmt))

    def milestones_achieved(self, project_id: int | None = None) -> int:
        stmt = select(func.count()).select_from(Milestone).where(Milestone.status == MilestoneStatus.COMPLETED)
        if project_id is not None:
            stmt = stmt.where(Milestone.project_id == project_id)
        return self.db.scalar(stmt) or 0

    def projects_completed(self, project_id: int | None = None) -> int:
        stmt = select(func.count()).select_from(Project).where(Project.status == ProjectStatus.COMPLETED)
        if project_id is not None:
            stmt = stmt.where(Project.id == project_id)
        return self.db.scalar(stmt) or 0
