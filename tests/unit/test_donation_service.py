from decimal import Decimal

import pytest

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.schemas.donation import DonationCreate, DonationUpdate
from app.services.donation_service import DonationService
from app.utils.enums import CampaignStatus, DonationMethod, DonationStatus, DonorStatus, Role
from tests.unit.factories import TODAY, mk_campaign, mk_donor
from datetime import timedelta


def payload(donor, campaign, amount="100.00", ref="REF-1", status=DonationStatus.CONFIRMED, **kw):
    return DonationCreate(
        donor_id=donor.id, campaign_id=campaign.id, amount=amount, donation_date=TODAY - timedelta(days=1),
        method=DonationMethod.UPI, reference_number=ref, status=status, **kw,
    )


@pytest.fixture()
def setup(db, make_user):
    return make_user(Role.FINANCE_OFFICER), mk_donor(db), mk_campaign(db)


def test_amount_must_be_positive(setup):
    _, donor, campaign = setup
    for bad in ("0", "-5"):
        with pytest.raises(ValueError):
            payload(donor, campaign, amount=bad)


def test_confirmed_donation_increases_campaign_total(db, setup):
    actor, donor, campaign = setup
    DonationService(db).create(actor, payload(donor, campaign, "250.50"))
    assert campaign.raised_amount == Decimal("250.50")


def test_pending_donation_does_not_change_total_until_confirmed(db, setup):
    actor, donor, campaign = setup
    svc = DonationService(db)
    d = svc.create(actor, payload(donor, campaign, "100", status=DonationStatus.PENDING))
    assert campaign.raised_amount == 0
    svc.change_status(actor, d.id, DonationStatus.CONFIRMED)
    assert campaign.raised_amount == Decimal("100.00")


def test_reverse_and_refund_deduct_from_campaign_total(db, setup):
    actor, donor, campaign = setup
    svc = DonationService(db)
    d1 = svc.create(actor, payload(donor, campaign, "300", ref="REF-A"))
    d2 = svc.create(actor, payload(donor, campaign, "200", ref="REF-B"))
    assert campaign.raised_amount == Decimal("500.00")
    svc.change_status(actor, d1.id, DonationStatus.REVERSED, "bank bounce")
    assert campaign.raised_amount == Decimal("200.00")
    svc.change_status(actor, d2.id, DonationStatus.REFUNDED, "donor request")
    assert campaign.raised_amount == Decimal("0.00")


def test_cancelled_pending_donation_never_counted(db, setup):
    actor, donor, campaign = setup
    svc = DonationService(db)
    d = svc.create(actor, payload(donor, campaign, status=DonationStatus.PENDING))
    svc.change_status(actor, d.id, DonationStatus.CANCELLED)
    assert campaign.raised_amount == 0


def test_terminal_states_cannot_change(db, setup):
    actor, donor, campaign = setup
    svc = DonationService(db)
    d = svc.create(actor, payload(donor, campaign))
    svc.change_status(actor, d.id, DonationStatus.REFUNDED)
    with pytest.raises(BusinessRuleError):
        svc.change_status(actor, d.id, DonationStatus.CONFIRMED)
    assert campaign.raised_amount == 0  # unchanged by the rejected attempt


def test_duplicate_reference_rejected(db, setup):
    actor, donor, campaign = setup
    svc = DonationService(db)
    svc.create(actor, payload(donor, campaign, ref="SAME"))
    with pytest.raises(ConflictError):
        svc.create(actor, payload(donor, campaign, ref="SAME"))
    assert campaign.raised_amount == Decimal("100.00")  # second attempt left no trace


@pytest.mark.parametrize("status", [CampaignStatus.COMPLETED, CampaignStatus.CANCELLED, CampaignStatus.DRAFT, CampaignStatus.PAUSED])
def test_closed_or_inactive_campaign_rejects_donations(db, make_user, status):
    actor, donor = make_user(Role.FINANCE_OFFICER), mk_donor(db)
    campaign = mk_campaign(db, status=status)
    with pytest.raises(BusinessRuleError):
        DonationService(db).create(actor, payload(donor, campaign))


def test_inactive_donor_cannot_donate(db, make_user):
    actor, campaign = make_user(Role.FINANCE_OFFICER), mk_campaign(db)
    donor = mk_donor(db, status=DonorStatus.BLOCKED)
    with pytest.raises(BusinessRuleError):
        DonationService(db).create(actor, payload(donor, campaign))


def test_unknown_donor_or_campaign(db, setup):
    actor, donor, campaign = setup
    bad = payload(donor, campaign).model_copy(update={"donor_id": 9999})
    with pytest.raises(NotFoundError):
        DonationService(db).create(actor, bad)


def test_financial_fields_locked_after_confirmation(db, setup):
    actor, donor, campaign = setup
    svc = DonationService(db)
    d = svc.create(actor, payload(donor, campaign))
    with pytest.raises(BusinessRuleError):
        svc.update(actor, d.id, DonationUpdate(amount="999"))
    assert svc.update(actor, d.id, DonationUpdate(notes="thanks")).notes == "thanks"


def test_pending_donation_amount_can_change(db, setup):
    actor, donor, campaign = setup
    svc = DonationService(db)
    d = svc.create(actor, payload(donor, campaign, status=DonationStatus.PENDING))
    assert svc.update(actor, d.id, DonationUpdate(amount="42.00")).amount == Decimal("42.00")
