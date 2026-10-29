from datetime import date

from sqlalchemy.orm import Session

from app.core.constants import PROJECT_CLOSED_STATUSES, PROJECT_TRANSITIONS, LIVE_ASSIGNMENT_STATUSES, assert_transition
from app.core.exceptions import BusinessRuleError, ForbiddenError, NotFoundError
from app.core.permissions import Permission, has_permission
from app.db.session import transaction
from app.models.project import Project
from app.models.user import User
from app.models.volunteer_assignment import VolunteerAssignment
from app.repositories.assignment_repository import AssignmentRepository
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.expense_repository import ExpenseRepository
from app.repositories.milestone_repository import MilestoneRepository
from app.repositories.project_repository import ApprovalRepository, ProjectRepository
from app.repositories.user_repository import UserRepository
from app.repositories.volunteer_repository import VolunteerRepository
from app.schemas.project import ProjectCreate, ProjectDetail, ProjectUpdate
from app.services.audit_service import AuditService, diff, snapshot
from app.utils.enums import ApprovalAction, AssignmentStatus, MilestoneStatus, ProjectStatus, Role
from app.utils.money import money, pct
from app.utils.pagination import PaginationParams
from app.utils.sorting import SortParams

AUDIT_FIELDS = ["name", "description", "objectives", "location", "start_date", "end_date", "budget", "status", "manager_id", "campaign_id"]
MANAGER_ROLES = {Role.SUPER_ADMIN, Role.NGO_MANAGER, Role.VOLUNTEER_COORDINATOR}


class ProjectService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ProjectRepository(db)
        self.approvals = ApprovalRepository(db)
        self.milestones = MilestoneRepository(db)
        self.audit = AuditService(db)

    # ------------------------------------------------------------------ serialisation / access
    def serialize(self, p: Project) -> ProjectDetail:
        out = ProjectDetail.model_validate(p)
        ms = self.milestones.for_project(p.id)
        done = sum(1 for m in ms if m.status == MilestoneStatus.COMPLETED)
        out.milestones_total, out.milestones_completed = len(ms), done
        out.milestone_completion_pct = pct(done, len(ms))
        latest = self.approvals.latest(p.id)
        out.approval_state = latest.action.value if latest else None
        return out

    def get_for_actor(self, actor: User, project_id: int) -> Project:
        p = self.repo.get(project_id)
        if not p:
            raise NotFoundError("Project not found")
        if has_permission(actor.role, Permission.PROJECTS_READ):
            return p
        if has_permission(actor.role, Permission.PROJECTS_READ_ASSIGNED):
            vol = VolunteerRepository(self.db).get_by_user_id(actor.id)
            if vol and self.repo.volunteer_has_access(vol.id, p.id):
                return p
        raise ForbiddenError("You do not have access to this project")

    def _validate_manager(self, manager_id: int | None) -> None:
        if manager_id is None:
            return
        user = UserRepository(self.db).get(manager_id)
        if not user or not user.is_active:
            raise NotFoundError("Project manager not found or inactive")
        if user.role not in MANAGER_ROLES:
            raise BusinessRuleError("A project manager must be a Super Admin, NGO Manager or Volunteer Coordinator")

    def _validate_campaign(self, campaign_id: int | None) -> None:
        if campaign_id is not None and not CampaignRepository(self.db).get(campaign_id):
            raise NotFoundError("Campaign not found")

    # ------------------------------------------------------------------ commands
    def create(self, actor: User, data: ProjectCreate) -> Project:
        manager_id = data.manager_id if data.manager_id is not None else (actor.id if actor.role in MANAGER_ROLES else None)
        self._validate_manager(manager_id)
        self._validate_campaign(data.campaign_id)
        with transaction(self.db):
            p = self.repo.add(
                Project(**data.model_dump(exclude={"manager_id", "budget"}), budget=money(data.budget), manager_id=manager_id, status=ProjectStatus.PLANNING)
            )
            self.audit.log(actor, "project.created", "project", p.id, snapshot(p, AUDIT_FIELDS))
        return p

    def update(self, actor: User, project_id: int, data: ProjectUpdate) -> Project:
        changes = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None or k in {"manager_id", "campaign_id", "description", "objectives", "location"}}
        with transaction(self.db):
            p = self.repo.get(project_id, for_update=True)
            if not p:
                raise NotFoundError("Project not found")
            if p.status in PROJECT_CLOSED_STATUSES:
                raise BusinessRuleError(f"A {p.status.value} project can no longer be edited")
            if "manager_id" in changes:
                self._validate_manager(changes["manager_id"])
            if "campaign_id" in changes:
                self._validate_campaign(changes["campaign_id"])
            start, end = changes.get("start_date", p.start_date), changes.get("end_date", p.end_date)
            if end < start:
                raise BusinessRuleError("end_date must be on or after start_date")
            if "budget" in changes:
                changes["budget"] = money(changes["budget"])
                spent = ExpenseRepository(self.db).spent_for_project(p.id)
                if changes["budget"] < spent:
                    raise BusinessRuleError(f"Budget cannot be lower than the approved expenses already spent ({spent})")
            before = snapshot(p, AUDIT_FIELDS)
            for k, v in changes.items():
                setattr(p, k, v)
            self.audit.log(actor, "project.updated", "project", p.id, diff(before, snapshot(p, AUDIT_FIELDS)))
        return p

    def _latest_decision(self, project_id: int) -> ApprovalAction | None:
        for rec in reversed(self.approvals.history(project_id)):
            if rec.action in (ApprovalAction.APPROVED, ApprovalAction.REJECTED):
                return rec.action
        return None

    def change_status(self, actor: User, project_id: int, target: ProjectStatus) -> Project:
        with transaction(self.db):
            p = self.repo.get(project_id, for_update=True)
            if not p:
                raise NotFoundError("Project not found")
            if target == ProjectStatus.APPROVED:
                raise BusinessRuleError("Projects become 'approved' only through the approval workflow")
            assert_transition(PROJECT_TRANSITIONS, p.status, target, "project status")
            if target == ProjectStatus.ACTIVE and self._latest_decision(p.id) != ApprovalAction.APPROVED:
                raise BusinessRuleError("A project cannot be activated until it has been approved")
            if target == ProjectStatus.COMPLETED:
                open_ms = [m for m in self.milestones.for_project(p.id) if m.status != MilestoneStatus.COMPLETED]
                if open_ms:
                    raise BusinessRuleError(f"Cannot complete the project: {len(open_ms)} milestone(s) are not completed")
            old = p.status
            p.status = target
            if target in PROJECT_CLOSED_STATUSES:
                self._close_live_assignments(p, completed=target == ProjectStatus.COMPLETED)
            self.audit.log(actor, f"project.{target.value}", "project", p.id, {"status": {"from": old, "to": target}})
        return p

    def _close_live_assignments(self, project: Project, *, completed: bool) -> None:
        repo = AssignmentRepository(self.db)
        live = self.db.query(VolunteerAssignment).filter(
            VolunteerAssignment.project_id == project.id, VolunteerAssignment.status.in_(LIVE_ASSIGNMENT_STATUSES)
        ).all()
        for a in live:
            a.status = AssignmentStatus.COMPLETED if (completed and a.status == AssignmentStatus.ACTIVE) else AssignmentStatus.CANCELLED
            self.db.flush()
            a.hours_completed = money(repo.total_hours(a.id))

    # ------------------------------------------------------------------ queries
    def list_projects(
        self, actor: User, params: PaginationParams, sort: SortParams, *, search: str | None, status: ProjectStatus | None,
        manager_id: int | None, campaign_id: int | None, location: str | None, date_from: date | None, date_to: date | None,
    ):
        only = None
        if not has_permission(actor.role, Permission.PROJECTS_READ):
            vol = VolunteerRepository(self.db).get_by_user_id(actor.id)
            only = AssignmentRepository(self.db).project_ids_for_volunteer(vol.id) if vol else set()
        return self.repo.list_projects(
            params, sort, search=search, status=status, manager_id=manager_id, campaign_id=campaign_id, location=location,
            date_from=date_from, date_to=date_to, only_project_ids=only,
        )
