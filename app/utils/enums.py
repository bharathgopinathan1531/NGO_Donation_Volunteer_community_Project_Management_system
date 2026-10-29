from enum import Enum


class Role(str, Enum):
    SUPER_ADMIN = "super_admin"
    NGO_MANAGER = "ngo_manager"
    FINANCE_OFFICER = "finance_officer"
    VOLUNTEER_COORDINATOR = "volunteer_coordinator"
    VOLUNTEER = "volunteer"
    DONOR = "donor"


class DonorType(str, Enum):
    INDIVIDUAL = "individual"
    ORGANIZATION = "organization"


class DonorStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"


class CampaignStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CampaignCategory(str, Enum):
    EDUCATION = "education"
    HEALTH = "health"
    FOOD = "food"
    DISASTER_RELIEF = "disaster_relief"
    ENVIRONMENT = "environment"
    LIVELIHOOD = "livelihood"
    OTHER = "other"


class DonationStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    REVERSED = "reversed"
    REFUNDED = "refunded"


class DonationMethod(str, Enum):
    CASH = "cash"
    CHEQUE = "cheque"
    BANK_TRANSFER = "bank_transfer"
    UPI = "upi"
    CARD = "card"
    ONLINE = "online"
    OTHER = "other"


class ReceiptStatus(str, Enum):
    ISSUED = "issued"
    VOID = "void"


class VolunteerStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ON_LEAVE = "on_leave"
    SUSPENDED = "suspended"


class AssignmentStatus(str, Enum):
    ASSIGNED = "assigned"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AttendanceStatus(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"
    EXCUSED = "excused"


class ProjectStatus(str, Enum):
    PLANNING = "planning"
    APPROVED = "approved"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ApprovalAction(str, Enum):
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class MilestoneStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ExpenseStatus(str, Enum):
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    REIMBURSED = "reimbursed"


class ExpenseCategory(str, Enum):
    MATERIALS = "materials"
    TRANSPORT = "transport"
    FOOD = "food"
    EQUIPMENT = "equipment"
    VENUE = "venue"
    STAFF = "staff"
    MEDICAL = "medical"
    ADMINISTRATIVE = "administrative"
    OTHER = "other"


class ResourceCategory(str, Enum):
    FOOD_PACKAGE = "food_package"
    CLOTHING = "clothing"
    EDUCATIONAL_MATERIAL = "educational_material"
    MEDICAL_SUPPLY = "medical_supply"
    EMERGENCY_KIT = "emergency_kit"
    OTHER = "other"


class StockTransactionType(str, Enum):
    STOCK_IN = "stock_in"
    STOCK_OUT = "stock_out"
    ALLOCATION = "allocation"


class BeneficiaryCategory(str, Enum):
    CHILD = "child"
    WOMAN = "woman"
    ELDERLY = "elderly"
    DISABLED = "disabled"
    FAMILY = "family"
    REFUGEE = "refugee"
    OTHER = "other"


class NotificationType(str, Enum):
    VOLUNTEER_ASSIGNMENT = "volunteer_assignment"
    PROJECT_APPROVAL_DECISION = "project_approval_decision"
    PROJECT_APPROVAL_REQUEST = "project_approval_request"
    PROJECT_DEADLINE = "project_deadline"
    MILESTONE_OVERDUE = "milestone_overdue"
    LOW_STOCK = "low_stock"
    EXPENSE_PENDING = "expense_pending"
    CAMPAIGN_CLOSING = "campaign_closing"
    BUDGET_OVERRUN = "budget_overrun"


class BudgetScope(str, Enum):
    CAMPAIGN = "campaign"
    PROJECT = "project"
