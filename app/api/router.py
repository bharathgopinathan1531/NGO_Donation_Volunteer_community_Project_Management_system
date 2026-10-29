from fastapi import APIRouter

from app.api.approvals.routes import router as approvals_router
from app.api.assignments.routes import router as assignments_router
from app.api.assistance.routes import router as assistance_router
from app.api.attendance.routes import router as attendance_router
from app.api.audit_logs.routes import router as audit_router
from app.api.auth.routes import router as auth_router
from app.api.beneficiaries.routes import router as beneficiaries_router
from app.api.budgets.routes import router as budgets_router
from app.api.campaigns.routes import router as campaigns_router
from app.api.dashboard.routes import router as dashboard_router
from app.api.donations.routes import router as donations_router
from app.api.donors.routes import router as donors_router
from app.api.expenses.routes import router as expenses_router
from app.api.health.routes import router as health_router
from app.api.impact.routes import router as impact_router
from app.api.milestones.routes import router as milestones_router
from app.api.notifications.routes import router as notifications_router
from app.api.projects.routes import router as projects_router
from app.api.receipts.routes import router as receipts_router
from app.api.reports.routes import router as reports_router
from app.api.resource_allocations.routes import router as allocations_router
from app.api.resources.routes import router as resources_router
from app.api.tasks.routes import router as tasks_router
from app.api.users.routes import router as users_router
from app.api.volunteers.routes import router as volunteers_router

api_router = APIRouter()
for r in (
    auth_router, users_router, donors_router, campaigns_router, donations_router, receipts_router, volunteers_router,
    assignments_router, attendance_router, projects_router, approvals_router, milestones_router, tasks_router,
    expenses_router, budgets_router, resources_router, allocations_router, beneficiaries_router, assistance_router,
    impact_router, notifications_router, dashboard_router, reports_router, audit_router,
):
    api_router.include_router(r)

health = health_router  # mounted separately (un-versioned) in main.py
