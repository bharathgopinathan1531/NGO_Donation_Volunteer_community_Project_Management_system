from datetime import date

from sqlalchemy.orm import Session

from app.core.constants import DONATION_TRANSITIONS, assert_transition
from app.core.exceptions import BusinessRuleError, ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import Permission, has_permission
from app.db.session import transaction
from app.models.donation import Donation
from app.models.user import User
from app.repositories.campaign_repository import CampaignRepository
from app.repositories.donation_repository import DonationRepository
from app.repositories.donor_repository import DonorRepository
from app.schemas.donation import DonationCreate, DonationUpdate
from app.services.audit_service import AuditService, diff, snapshot
from app.services.receipt_service import ReceiptService
from app.utils.date_utils import today
from app.utils.enums import CampaignStatus, DonationMethod, DonationStatus, DonorStatus
from app.utils.money import money
from app.utils.pagination import PaginationParams
from app.utils.sorting import SortParams

AUDIT_FIELDS = ["donor_id", "campaign_id", "amount", "donation_date", "method", "reference_number", "status", "notes"]


class DonationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DonationRepository(db)
        self.campaigns = CampaignRepository(db)
        self.donors = DonorRepository(db)
        self.audit = AuditService(db)

    # ------------------------------------------------------------------ helpers
    def _own_donor_id(self, actor: User) -> int | None:
        donor = self.donors.get_by_user_id(actor.id)
        return donor.id if donor else None

    def get_for_actor(self, actor: User, donation_id: int) -> Donation:
        d = self.repo.get(donation_id)
        if not d:
            raise NotFoundError("Donation not found")
        if has_permission(actor.role, Permission.DONATIONS_READ):
            return d
        if has_permission(actor.role, Permission.DONATIONS_READ_OWN) and d.donor_id == self._own_donor_id(actor):
            return d
        raise ForbiddenError("You do not have access to this donation")

    # ------------------------------------------------------------------ commands
    def create(self, actor: User, data: DonationCreate) -> Donation:
        reference = data.reference_number.strip()
        if data.donation_date > today():
            raise BusinessRuleError("Donation date cannot be in the future")
        with transaction(self.db):
            donor = self.donors.get(data.donor_id)
            if not donor:
                raise NotFoundError("Donor not found")
            if donor.status != DonorStatus.ACTIVE:
                raise BusinessRuleError(f"Donor is {donor.status.value}; donations cannot be recorded")
            campaign = self.campaigns.get(data.campaign_id, for_update=True)
            if not campaign:
                raise NotFoundError("Campaign not found")
            if campaign.status != CampaignStatus.ACTIVE:
                raise BusinessRuleError(
                    f"Campaign is {campaign.status.value}; donations are accepted only while a campaign is active"
                )
            if self.repo.get_by_reference(reference):
                raise ConflictError(f"Donation reference '{reference}' already exists")
            donation = self.repo.add(
                Donation(
                    donor_id=donor.id, campaign_id=campaign.id, amount=money(data.amount), donation_date=data.donation_date,
                    method=data.method, reference_number=reference, status=data.status, notes=data.notes, recorded_by=actor.id,
                )
            )
            if donation.status == DonationStatus.CONFIRMED:
                campaign.raised_amount = money(campaign.raised_amount) + donation.amount
            self.audit.log(actor, "donation.created", "donation", donation.id, snapshot(donation, AUDIT_FIELDS))
        return donation

    def update(self, actor: User, donation_id: int, data: DonationUpdate) -> Donation:
        changes = data.model_dump(exclude_unset=True)
        with transaction(self.db):
            d = self.repo.get(donation_id, for_update=True)
            if not d:
                raise NotFoundError("Donation not found")
            financial = {k for k in ("amount", "donation_date", "method") if k in changes}
            if financial and d.status != DonationStatus.PENDING:
                raise BusinessRuleError(
                    "Only pending donations can change amount, date or method; reverse or refund a confirmed donation instead"
                )
            if "donation_date" in changes and changes["donation_date"] and changes["donation_date"] > today():
                raise BusinessRuleError("Donation date cannot be in the future")
            for k, v in list(changes.items()):
                if v is None and k != "notes":
                    changes.pop(k)
            before = snapshot(d, AUDIT_FIELDS)
            for k, v in changes.items():
                setattr(d, k, money(v) if k == "amount" else v)
            self.audit.log(actor, "donation.updated", "donation", d.id, diff(before, snapshot(d, AUDIT_FIELDS)))
        return d

    def change_status(self, actor: User, donation_id: int, target: DonationStatus, reason: str | None = None) -> Donation:
        """confirm / cancel / reverse / refund, keeping campaign totals and receipts consistent in ONE transaction."""
        with transaction(self.db):
            d = self.repo.get(donation_id, for_update=True)
            if not d:
                raise NotFoundError("Donation not found")
            assert_transition(DONATION_TRANSITIONS, d.status, target, "donation status")
            campaign = self.campaigns.get(d.campaign_id, for_update=True)
            old = d.status
            if target == DonationStatus.CONFIRMED:
                if campaign.status == CampaignStatus.CANCELLED:
                    raise BusinessRuleError("Cannot confirm a donation for a cancelled campaign")
                campaign.raised_amount = money(campaign.raised_amount) + d.amount
            elif old == DonationStatus.CONFIRMED and target in (DonationStatus.REVERSED, DonationStatus.REFUNDED):
                new_total = money(campaign.raised_amount) - d.amount
                if new_total < 0:
                    raise BusinessRuleError("Campaign totals are inconsistent; cannot deduct this donation")
                campaign.raised_amount = new_total
                ReceiptService(self.db).void_for_donation(actor, d, reason or f"Donation {target.value}")
            d.status = target
            self.audit.log(
                actor, f"donation.{target.value}", "donation", d.id,
                {"status": {"from": old, "to": target}, "amount": d.amount, "campaign_id": campaign.id,
                 "campaign_raised_amount": campaign.raised_amount, "reason": reason},
            )
        return d

    # ------------------------------------------------------------------ queries
    def list_donations(
        self, actor: User, params: PaginationParams, sort: SortParams, *, donor_id: int | None, campaign_id: int | None,
        status: DonationStatus | None, method: DonationMethod | None, search: str | None, date_from: date | None, date_to: date | None,
    ):
        if not has_permission(actor.role, Permission.DONATIONS_READ):
            own = self._own_donor_id(actor)
            if own is None:
                return [], 0
            if donor_id is not None and donor_id != own:
                raise ForbiddenError("You can only list your own donations")
            donor_id = own
        return self.repo.list_donations(
            params, sort, donor_id=donor_id, campaign_id=campaign_id, status=status, method=method, search=search,
            date_from=date_from, date_to=date_to,
        )
