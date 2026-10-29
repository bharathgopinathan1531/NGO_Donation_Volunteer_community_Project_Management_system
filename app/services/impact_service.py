from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.session import transaction
from app.models.impact_update import ImpactUpdate
from app.models.user import User
from app.repositories.impact_repository import ImpactRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.impact import ImpactSummary, ImpactUpdateCreate
from app.services.audit_service import AuditService
from app.utils.enums import ProjectStatus
from app.utils.money import money
from app.utils.pagination import PaginationParams


class ImpactService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ImpactRepository(db)
        self.projects = ProjectRepository(db)
        self.audit = AuditService(db)

    def live_summary(self, project_id: int | None = None) -> ImpactSummary:
        if project_id is not None and not self.projects.get(project_id):
            raise NotFoundError("Project not found")
        r = self.repo
        return ImpactSummary(
            project_id=project_id,
            beneficiaries_served=r.beneficiaries_served(project_id),
            volunteer_hours=r.volunteer_hours(project_id),
            resources_distributed=r.resources_distributed(project_id),
            projects_completed=r.projects_completed(project_id),
            funds_utilized=r.funds_utilized(project_id),
            milestones_achieved=r.milestones_achieved(project_id),
        )

    def submit(self, actor: User, data: ImpactUpdateCreate) -> ImpactUpdate:
        """Anything the manager leaves blank is filled from live database records."""
        with transaction(self.db):
            p = self.projects.get(data.project_id)
            if not p:
                raise NotFoundError("Project not found")
            live = self.live_summary(p.id)
            update = self.repo.add(
                ImpactUpdate(
                    project_id=p.id,
                    beneficiaries_served=data.beneficiaries_served if data.beneficiaries_served is not None else live.beneficiaries_served,
                    volunteer_hours=money(data.volunteer_hours) if data.volunteer_hours is not None else live.volunteer_hours,
                    resources_distributed=data.resources_distributed if data.resources_distributed is not None else live.resources_distributed,
                    funds_utilized=money(data.funds_utilized) if data.funds_utilized is not None else live.funds_utilized,
                    milestones_achieved=data.milestones_achieved if data.milestones_achieved is not None else live.milestones_achieved,
                    project_completed=p.status == ProjectStatus.COMPLETED,
                    notes=data.notes,
                    submitted_by=actor.id,
                )
            )
            self.audit.log(
                actor, "impact.submitted", "impact_update", update.id,
                {"project_id": p.id, "beneficiaries_served": update.beneficiaries_served, "volunteer_hours": update.volunteer_hours,
                 "resources_distributed": update.resources_distributed, "funds_utilized": update.funds_utilized,
                 "milestones_achieved": update.milestones_achieved},
            )
        return update

    def history(self, params: PaginationParams, project_id: int | None):
        return self.repo.history(params, project_id)
