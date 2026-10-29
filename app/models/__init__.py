"""Import every model so SQLAlchemy metadata (and Alembic autogenerate) sees all tables."""
from app.models.attendance import Attendance
from app.models.audit_log import AuditLog
from app.models.beneficiary import Beneficiary, beneficiary_projects
from app.models.beneficiary_assistance import BeneficiaryAssistance
from app.models.budget import Budget
from app.models.campaign import Campaign
from app.models.donation import Donation
from app.models.donor import Donor
from app.models.expense import Expense
from app.models.impact_update import ImpactUpdate
from app.models.milestone import Milestone
from app.models.notification import Notification
from app.models.password_reset_token import PasswordResetToken
from app.models.project import Project
from app.models.project_approval import ProjectApproval
from app.models.receipt import Receipt
from app.models.refresh_token import RefreshToken
from app.models.resource import Resource
from app.models.resource_allocation import ResourceAllocation
from app.models.stock_transaction import StockTransaction
from app.models.task import Task
from app.models.user import User
from app.models.volunteer import Volunteer
from app.models.volunteer_assignment import VolunteerAssignment

__all__ = [
    "Attendance", "AuditLog", "Beneficiary", "beneficiary_projects", "BeneficiaryAssistance", "Budget", "Campaign",
    "Donation", "Donor", "Expense", "ImpactUpdate", "Milestone", "Notification", "PasswordResetToken", "Project",
    "ProjectApproval", "Receipt", "RefreshToken", "Resource", "ResourceAllocation", "StockTransaction", "Task",
    "User", "Volunteer", "VolunteerAssignment",
]
