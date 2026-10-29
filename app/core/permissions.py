"""Permission-based RBAC. Roles map to sets of permissions; endpoints require permissions."""
from enum import Enum

from app.utils.enums import Role


class Permission(str, Enum):
    USERS_MANAGE = "users:manage"
    DONORS_READ = "donors:read"
    DONORS_WRITE = "donors:write"
    DONORS_READ_OWN = "donors:read_own"
    CAMPAIGNS_READ = "campaigns:read"
    CAMPAIGNS_WRITE = "campaigns:write"
    DONATIONS_READ = "donations:read"
    DONATIONS_WRITE = "donations:write"
    DONATIONS_READ_OWN = "donations:read_own"
    RECEIPTS_READ = "receipts:read"
    RECEIPTS_WRITE = "receipts:write"
    RECEIPTS_READ_OWN = "receipts:read_own"
    VOLUNTEERS_READ = "volunteers:read"
    VOLUNTEERS_WRITE = "volunteers:write"
    VOLUNTEERS_REGISTER_SELF = "volunteers:register_self"
    ASSIGNMENTS_READ = "assignments:read"
    ASSIGNMENTS_WRITE = "assignments:write"
    ASSIGNMENTS_READ_OWN = "assignments:read_own"
    ATTENDANCE_WRITE = "attendance:write"
    PROJECTS_READ = "projects:read"
    PROJECTS_READ_ASSIGNED = "projects:read_assigned"
    PROJECTS_WRITE = "projects:write"
    PROJECTS_SUBMIT = "projects:submit"
    PROJECTS_APPROVE = "projects:approve"
    MILESTONES_WRITE = "milestones:write"
    TASKS_WRITE = "tasks:write"
    TASKS_UPDATE_OWN = "tasks:update_own"
    EXPENSES_SUBMIT = "expenses:submit"
    EXPENSES_READ = "expenses:read"
    EXPENSES_APPROVE = "expenses:approve"
    BUDGETS_READ = "budgets:read"
    BUDGETS_WRITE = "budgets:write"
    RESOURCES_READ = "resources:read"
    RESOURCES_WRITE = "resources:write"
    BENEFICIARIES_READ = "beneficiaries:read"
    BENEFICIARIES_WRITE = "beneficiaries:write"
    BENEFICIARIES_SENSITIVE = "beneficiaries:sensitive"
    IMPACT_READ = "impact:read"
    IMPACT_WRITE = "impact:write"
    NOTIFICATIONS_MANAGE = "notifications:manage"
    DASHBOARD_READ = "dashboard:read"
    REPORTS_FINANCE = "reports:finance"
    REPORTS_OPERATIONS = "reports:operations"
    AUDIT_READ = "audit:read"


P = Permission

_MANAGER = {
    P.DONORS_READ, P.DONORS_WRITE, P.CAMPAIGNS_READ, P.CAMPAIGNS_WRITE, P.DONATIONS_READ, P.DONATIONS_WRITE,
    P.RECEIPTS_READ, P.RECEIPTS_WRITE, P.VOLUNTEERS_READ, P.VOLUNTEERS_WRITE, P.ASSIGNMENTS_READ,
    P.ASSIGNMENTS_WRITE, P.ATTENDANCE_WRITE, P.PROJECTS_READ, P.PROJECTS_WRITE, P.PROJECTS_SUBMIT,
    P.PROJECTS_APPROVE, P.MILESTONES_WRITE, P.TASKS_WRITE, P.EXPENSES_SUBMIT, P.EXPENSES_READ, P.BUDGETS_READ,
    P.BUDGETS_WRITE, P.RESOURCES_READ, P.RESOURCES_WRITE, P.BENEFICIARIES_READ, P.BENEFICIARIES_WRITE,
    P.BENEFICIARIES_SENSITIVE, P.IMPACT_READ, P.IMPACT_WRITE, P.NOTIFICATIONS_MANAGE, P.DASHBOARD_READ,
    P.REPORTS_FINANCE, P.REPORTS_OPERATIONS, P.AUDIT_READ,
}

ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.SUPER_ADMIN: set(Permission),
    Role.NGO_MANAGER: _MANAGER,
    Role.FINANCE_OFFICER: {
        P.DONORS_READ, P.CAMPAIGNS_READ, P.DONATIONS_READ, P.DONATIONS_WRITE, P.RECEIPTS_READ, P.RECEIPTS_WRITE,
        P.PROJECTS_READ, P.EXPENSES_SUBMIT, P.EXPENSES_READ, P.EXPENSES_APPROVE, P.BUDGETS_READ, P.BUDGETS_WRITE,
        P.RESOURCES_READ, P.DASHBOARD_READ, P.REPORTS_FINANCE, P.IMPACT_READ,
    },
    Role.VOLUNTEER_COORDINATOR: {
        P.CAMPAIGNS_READ, P.VOLUNTEERS_READ, P.VOLUNTEERS_WRITE, P.ASSIGNMENTS_READ, P.ASSIGNMENTS_WRITE,
        P.ATTENDANCE_WRITE, P.PROJECTS_READ, P.PROJECTS_SUBMIT, P.MILESTONES_WRITE, P.TASKS_WRITE,
        P.EXPENSES_SUBMIT, P.EXPENSES_READ, P.RESOURCES_READ, P.BENEFICIARIES_READ, P.BENEFICIARIES_WRITE,
        P.IMPACT_READ, P.DASHBOARD_READ, P.REPORTS_OPERATIONS,
    },
    Role.VOLUNTEER: {
        P.VOLUNTEERS_REGISTER_SELF, P.ASSIGNMENTS_READ_OWN, P.PROJECTS_READ_ASSIGNED, P.TASKS_UPDATE_OWN,
        P.CAMPAIGNS_READ,
    },
    Role.DONOR: {P.DONORS_READ_OWN, P.DONATIONS_READ_OWN, P.RECEIPTS_READ_OWN, P.CAMPAIGNS_READ},
}


def has_permission(role: Role, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())


STAFF_ROLES = {Role.SUPER_ADMIN, Role.NGO_MANAGER, Role.FINANCE_OFFICER, Role.VOLUNTEER_COORDINATOR}
PRIVILEGED_ROLES = {Role.SUPER_ADMIN, Role.NGO_MANAGER}
SELF_REGISTRATION_ROLES = {Role.VOLUNTEER, Role.DONOR}
