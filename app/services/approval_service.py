from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import PRIVILEGED_ROLES
from app.db.session import transaction
from app.models.project_approval import ProjectApproval
from app.models.user import User
from app.repositories.project_repository import ApprovalRepository, ProjectRepository
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService
from app.services.project_service import ProjectService
from app.utils.enums import ApprovalAction, NotificationType, ProjectStatus, Role
from app.utils.pagination import PaginationParams


class ApprovalService:
    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)
        self.repo = ApprovalRepository(db)
        self.audit = AuditService(db)
        self.notifications = NotificationService(db)

    def submit(self, actor: User, project_id: int, comments: str | None) -> ProjectApproval:
        with transaction(self.db):
            p = self.projects.get(project_id, for_update=True)
            if not p:
                raise NotFoundError("Project not found")
            if p.status != ProjectStatus.PLANNING:
                raise BusinessRuleError(f"Only projects in 'planning' can be submitted for approval (this one is '{p.status.value}')")
            latest = self.repo.latest(p.id)
            if latest and latest.action == ApprovalAction.SUBMITTED:
                raise ConflictError("This project is already awaiting approval")
            rec = self.repo.add(ProjectApproval(project_id=p.id, action=ApprovalAction.SUBMITTED, comments=comments, actor_id=actor.id))
            self.notifications.notify_roles(
                set(PRIVILEGED_ROLES), NotificationType.PROJECT_APPROVAL_REQUEST, "Project awaiting approval",
                f"Project '{p.name}' was submitted for approval.", exclude_user_id=actor.id, entity="project", entity_id=p.id,
                dedupe_key=f"approval_request:{rec.id}",
            )
            self.audit.log(actor, "project.submitted", "project", p.id, {"comments": comments})
        return rec

    def _decide(self, actor: User, project_id: int, approve: bool, comments: str | None) -> ProjectApproval:
        with transaction(self.db):
            p = self.projects.get(project_id, for_update=True)
            if not p:
                raise NotFoundError("Project not found")
            latest = self.repo.latest(p.id)
            if p.status != ProjectStatus.PLANNING or not latest or latest.action != ApprovalAction.SUBMITTED:
                raise BusinessRuleError("This project is not awaiting an approval decision")
            if latest.actor_id == actor.id and actor.role != Role.SUPER_ADMIN:
                raise ForbiddenError("You cannot decide on a project that you submitted yourself")
            action = ApprovalAction.APPROVED if approve else ApprovalAction.REJECTED
            rec = self.repo.add(ProjectApproval(project_id=p.id, action=action, comments=comments, actor_id=actor.id))
            if approve:
                p.status = ProjectStatus.APPROVED
            self.notifications.notify(
                {latest.actor_id, p.manager_id} - {actor.id}, NotificationType.PROJECT_APPROVAL_DECISION,
                f"Project {action.value}", f"Project '{p.name}' was {action.value}." + (f" Comments: {comments}" if comments else ""),
                entity="project", entity_id=p.id, dedupe_key=f"approval_decision:{rec.id}",
            )
            self.audit.log(actor, f"project.{action.value}", "project", p.id, {"comments": comments, "status": p.status})
        return rec

    def approve(self, actor: User, project_id: int, comments: str | None) -> ProjectApproval:
        return self._decide(actor, project_id, True, comments)

    def reject(self, actor: User, project_id: int, comments: str) -> ProjectApproval:
        return self._decide(actor, project_id, False, comments)

    def history(self, actor: User, project_id: int) -> list[ProjectApproval]:
        ProjectService(self.db).get_for_actor(actor, project_id)
        return self.repo.history(project_id)

    def pending(self, params: PaginationParams):
        return self.repo.list_pending(params)
