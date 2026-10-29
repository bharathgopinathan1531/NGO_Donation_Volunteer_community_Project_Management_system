from collections import Counter
from typing import Iterable

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.permissions import PRIVILEGED_ROLES
from app.db.session import transaction
from app.models.notification import Notification
from app.models.user import User
from app.repositories.budget_repository import BudgetRepository
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.expense_repository import ExpenseRepository
from app.repositories.milestone_repository import MilestoneRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.resource_repository import ResourceRepository
from app.repositories.user_repository import UserRepository
from app.utils.date_utils import today, utcnow
from app.utils.enums import NotificationType, Role
from app.utils.pagination import PaginationParams


class NotificationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = NotificationRepository(db)
        self.users = UserRepository(db)

    # ------------------------------------------------------------------ creation (runs in caller's transaction)
    def notify(
        self, user_ids: Iterable[int | None], type: NotificationType, title: str, message: str, *,
        entity: str | None = None, entity_id: int | None = None, dedupe_key: str | None = None,
    ) -> int:
        created = 0
        for uid in {u for u in user_ids if u}:
            if dedupe_key and self.repo.exists(uid, dedupe_key):
                continue
            self.repo.add(
                Notification(user_id=uid, type=type, title=title, message=message, entity=entity, entity_id=entity_id, dedupe_key=dedupe_key)
            )
            created += 1
        return created

    def notify_roles(self, roles: set[Role], type: NotificationType, title: str, message: str, *, exclude_user_id: int | None = None, **kw) -> int:
        ids = [u.id for u in self.users.active_by_roles(roles) if u.id != exclude_user_id]
        return self.notify(ids, type, title, message, **kw)

    def privileged_ids(self) -> list[int]:
        return [u.id for u in self.users.active_by_roles(set(PRIVILEGED_ROLES))]

    # ------------------------------------------------------------------ inbox
    def list_mine(self, user: User, params: PaginationParams, *, unread_only: bool, type: NotificationType | None):
        return self.repo.list_for_user(user.id, params, unread_only=unread_only, type=type)

    def unread_count(self, user: User) -> int:
        return self.repo.unread_count(user.id)

    def mark_read(self, user: User, notification_id: int, read: bool = True) -> Notification:
        with transaction(self.db):
            n = self.repo.get(notification_id)
            if not n:
                raise NotFoundError("Notification not found")
            if n.user_id != user.id:
                raise ForbiddenError("This notification belongs to another user")
            n.is_read = read
            n.read_at = utcnow() if read else None
        return n

    def mark_all_read(self, user: User) -> int:
        with transaction(self.db):
            return self.repo.mark_all_read(user.id)

    # ------------------------------------------------------------------ scheduled scans (call via API or cron)
    def generate_scheduled(self) -> dict:
        """Scan the database for time/state based alerts. Idempotent thanks to per-user dedupe keys."""
        from app.services.budget_service import BudgetService  # local import avoids a cycle

        counts: Counter = Counter()
        now = today()
        privileged = self.privileged_ids()
        days = settings.DEADLINE_ALERT_DAYS

        with transaction(self.db):
            for p in ProjectRepository(self.db).ending_soon(now, days):
                counts[NotificationType.PROJECT_DEADLINE.value] += self.notify(
                    [p.manager_id] if p.manager_id else privileged, NotificationType.PROJECT_DEADLINE,
                    "Project deadline approaching", f"Project '{p.name}' ends on {p.end_date.isoformat()}.",
                    entity="project", entity_id=p.id, dedupe_key=f"project_deadline:{p.id}:{p.end_date.isoformat()}",
                )
            for m in MilestoneRepository(self.db).overdue(now):
                project = ProjectRepository(self.db).get(m.project_id)
                recipients = [project.manager_id] if project and project.manager_id else privileged
                counts[NotificationType.MILESTONE_OVERDUE.value] += self.notify(
                    recipients, NotificationType.MILESTONE_OVERDUE, "Milestone overdue",
                    f"Milestone '{m.title}' was due on {m.due_date.isoformat()}.",
                    entity="milestone", entity_id=m.id, dedupe_key=f"milestone_overdue:{m.id}:{m.due_date.isoformat()}",
                )
            for c in CampaignRepository(self.db).closing_soon(now, days):
                counts[NotificationType.CAMPAIGN_CLOSING.value] += self.notify(
                    [c.manager_id] if c.manager_id else privileged, NotificationType.CAMPAIGN_CLOSING,
                    "Campaign closing soon", f"Campaign '{c.title}' closes on {c.end_date.isoformat()}.",
                    entity="campaign", entity_id=c.id, dedupe_key=f"campaign_closing:{c.id}:{c.end_date.isoformat()}",
                )
            for r in ResourceRepository(self.db).low_stock():
                counts[NotificationType.LOW_STOCK.value] += self.notify(
                    privileged, NotificationType.LOW_STOCK, "Low stock",
                    f"'{r.name}' is low: {r.quantity} {r.unit} left (threshold {r.low_stock_threshold}).",
                    entity="resource", entity_id=r.id, dedupe_key=f"low_stock:{r.id}:{now.isoformat()}",
                )
            for e in ExpenseRepository(self.db).pending():
                counts[NotificationType.EXPENSE_PENDING.value] += self.notify_roles(
                    {Role.FINANCE_OFFICER, Role.SUPER_ADMIN}, NotificationType.EXPENSE_PENDING, "Expense awaiting approval",
                    f"Expense #{e.id} of {e.amount} is pending review.", entity="expense", entity_id=e.id, dedupe_key=f"expense_pending:{e.id}",
                )
            for u in BudgetService(self.db).list_utilization(only_overruns=True):
                recipients = set(privileged) | {x.id for x in self.users.active_by_roles({Role.FINANCE_OFFICER})}
                counts[NotificationType.BUDGET_OVERRUN.value] += self.notify(
                    recipients, NotificationType.BUDGET_OVERRUN, "Budget overrun",
                    f"{u.scope.value.title()} '{u.entity_name}' has spent {u.spent} against a budget of {u.budget}.",
                    entity=u.scope.value, entity_id=u.entity_id, dedupe_key=f"budget_overrun:{u.scope.value}:{u.entity_id}",
                )
        return {"created": sum(counts.values()), "by_type": dict(counts)}
