from datetime import date

from sqlalchemy.orm import Session

from app.core.constants import CAMPAIGN_TRANSITIONS, CLOSED_CAMPAIGN_STATUSES, assert_transition
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.permissions import PRIVILEGED_ROLES
from app.db.session import transaction
from app.models.campaign import Campaign
from app.models.user import User
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.user_repository import UserRepository
from app.schemas.campaign import CampaignCreate, CampaignOut, CampaignUpdate
from app.services.audit_service import AuditService, diff, snapshot
from app.utils.date_utils import today
from app.utils.enums import CampaignCategory, CampaignStatus, Role
from app.utils.money import money, pct
from app.utils.pagination import PaginationParams
from app.utils.sorting import SortParams

AUDIT_FIELDS = ["title", "description", "category", "goal_amount", "start_date", "end_date", "manager_id", "status"]
PUBLIC_ROLES = {Role.VOLUNTEER, Role.DONOR}  # may only see active campaigns


class CampaignService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CampaignRepository(db)
        self.users = UserRepository(db)
        self.audit = AuditService(db)

    @staticmethod
    def serialize(c: Campaign) -> CampaignOut:
        out = CampaignOut.model_validate(c)
        out.achievement_pct = pct(c.raised_amount, c.goal_amount)
        out.remaining_amount = max(money(c.goal_amount) - money(c.raised_amount), money(0))
        return out

    def _validate_manager(self, manager_id: int | None) -> None:
        if manager_id is None:
            return
        user = self.users.get(manager_id)
        if not user or not user.is_active:
            raise NotFoundError("Campaign manager not found or inactive")
        if user.role not in PRIVILEGED_ROLES:
            raise BusinessRuleError("A campaign manager must be an NGO Manager or Super Admin")

    def _get(self, campaign_id: int) -> Campaign:
        c = self.repo.get(campaign_id)
        if not c:
            raise NotFoundError("Campaign not found")
        return c

    def get_for_actor(self, actor: User, campaign_id: int) -> Campaign:
        c = self._get(campaign_id)
        if actor.role in PUBLIC_ROLES and c.status != CampaignStatus.ACTIVE:
            raise NotFoundError("Campaign not found")
        return c

    def create(self, actor: User, data: CampaignCreate) -> Campaign:
        manager_id = data.manager_id if data.manager_id is not None else (actor.id if actor.role in PRIVILEGED_ROLES else None)
        self._validate_manager(manager_id)
        with transaction(self.db):
            c = self.repo.add(
                Campaign(**data.model_dump(exclude={"manager_id"}), manager_id=manager_id, status=CampaignStatus.DRAFT, raised_amount=money(0))
            )
            self.audit.log(actor, "campaign.created", "campaign", c.id, snapshot(c, AUDIT_FIELDS))
        return c

    def update(self, actor: User, campaign_id: int, data: CampaignUpdate) -> Campaign:
        changes = data.model_dump(exclude_unset=True)
        with transaction(self.db):
            c = self.repo.get(campaign_id, for_update=True)
            if not c:
                raise NotFoundError("Campaign not found")
            if c.status in CLOSED_CAMPAIGN_STATUSES:
                raise BusinessRuleError(f"A {c.status.value} campaign can no longer be edited")
            if "manager_id" in changes:
                self._validate_manager(changes["manager_id"])
            start = changes.get("start_date", c.start_date)
            end = changes.get("end_date", c.end_date)
            if end < start:
                raise BusinessRuleError("end_date must be on or after start_date")
            if c.status == CampaignStatus.ACTIVE and end < today():
                raise BusinessRuleError("An active campaign cannot end in the past")
            for field in ("title", "goal_amount", "start_date", "end_date", "category"):
                if field in changes and changes[field] is None:
                    raise BusinessRuleError(f"{field} cannot be null")
            before = snapshot(c, AUDIT_FIELDS)
            for k, v in changes.items():
                setattr(c, k, v)
            self.audit.log(actor, "campaign.updated", "campaign", c.id, diff(before, snapshot(c, AUDIT_FIELDS)))
        return c

    def change_status(self, actor: User, campaign_id: int, target: CampaignStatus) -> Campaign:
        with transaction(self.db):
            c = self.repo.get(campaign_id, for_update=True)
            if not c:
                raise NotFoundError("Campaign not found")
            assert_transition(CAMPAIGN_TRANSITIONS, c.status, target, "campaign status")
            if target == CampaignStatus.ACTIVE and c.end_date < today():
                raise BusinessRuleError("Cannot activate a campaign whose end date has passed")
            old = c.status
            c.status = target
            self.audit.log(
                actor, f"campaign.{target.value}", "campaign", c.id,
                {"status": {"from": old, "to": target}, "raised_amount": c.raised_amount, "goal_amount": c.goal_amount},
            )
        return c

    def list_campaigns(
        self, actor: User, params: PaginationParams, sort: SortParams, *, search: str | None, status: CampaignStatus | None,
        category: CampaignCategory | None, manager_id: int | None, date_from: date | None, date_to: date | None,
    ):
        if actor.role in PUBLIC_ROLES:
            status = CampaignStatus.ACTIVE
        return self.repo.list_campaigns(
            params, sort, search=search, status=status, category=category, manager_id=manager_id, date_from=date_from, date_to=date_to
        )
