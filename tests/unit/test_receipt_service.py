import re

import pytest

from app.core.exceptions import BusinessRuleError, ConflictError, ForbiddenError
from app.services.donation_service import DonationService
from app.services.receipt_service import ReceiptService
from app.utils.enums import DonationStatus, ReceiptStatus, Role
from app.utils.receipt_number import generate_receipt_number
from tests.unit.factories import mk_campaign, mk_donation, mk_donor


@pytest.fixture()
def setup(db, make_user):
    donor, campaign = mk_donor(db), mk_campaign(db)
    return make_user(Role.FINANCE_OFFICER), donor, campaign


def test_receipt_issued_for_confirmed_donation_with_metadata(db, setup):
    actor, donor, campaign = setup
    donation = mk_donation(db, donor, campaign, "750.00", ref="R-1")
    receipt = ReceiptService(db).issue(actor, donation.id)
    assert re.fullmatch(r"RCT-\d{8}-[A-Z2-9]{8}", receipt.receipt_number)
    assert receipt.amount == donation.amount and receipt.donor_id == donor.id and receipt.status == ReceiptStatus.ISSUED
    assert receipt.meta["donation_reference"] == "R-1" and receipt.meta["campaign_title"] == campaign.title


def test_duplicate_receipt_is_prevented(db, setup):
    actor, donor, campaign = setup
    donation = mk_donation(db, donor, campaign)
    svc = ReceiptService(db)
    svc.issue(actor, donation.id)
    with pytest.raises(ConflictError):
        svc.issue(actor, donation.id)


@pytest.mark.parametrize("status", [DonationStatus.PENDING, DonationStatus.CANCELLED, DonationStatus.REFUNDED, DonationStatus.REVERSED])
def test_only_confirmed_donations_get_receipts(db, setup, status):
    actor, donor, campaign = setup
    donation = mk_donation(db, donor, campaign, status=status)
    with pytest.raises(BusinessRuleError):
        ReceiptService(db).issue(actor, donation.id)


def test_refund_voids_the_receipt(db, setup):
    actor, donor, campaign = setup
    donation = mk_donation(db, donor, campaign, "100.00")
    receipt = ReceiptService(db).issue(actor, donation.id)
    DonationService(db).change_status(actor, donation.id, DonationStatus.REFUNDED, "donor request")
    db.refresh(receipt)
    assert receipt.status == ReceiptStatus.VOID and receipt.void_reason == "donor request" and receipt.voided_at
    with pytest.raises(BusinessRuleError):  # a refunded donation can never be receipted again
        ReceiptService(db).issue(actor, donation.id)


def test_receipt_numbers_are_unique():
    assert len({generate_receipt_number() for _ in range(500)}) == 500


def test_donor_can_only_read_their_own_receipts(db, setup, make_user):
    actor, donor, campaign = setup
    donor_user = make_user(Role.DONOR, "mydonor@example.org")
    donor.user_id = donor_user.id
    db.commit()
    mine = ReceiptService(db).issue(actor, mk_donation(db, donor, campaign, ref="M1").id)
    other_donor = mk_donor(db, "Other", "o@example.org")
    theirs = ReceiptService(db).issue(actor, mk_donation(db, other_donor, campaign, ref="O1").id)
    assert ReceiptService(db).get(donor_user, mine.id).id == mine.id
    with pytest.raises(ForbiddenError):
        ReceiptService(db).get(donor_user, theirs.id)
