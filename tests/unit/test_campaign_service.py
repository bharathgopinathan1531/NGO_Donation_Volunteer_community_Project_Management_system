from datetime import timedelta

import pytest

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.schemas.campaign import CampaignCreate, CampaignUpdate
from app.services.campaign_service import CampaignService
from app.utils.enums import CampaignStatus, Role
from tests.unit.factories import TODAY, mk_campaign


def payload(**kw):
    base = dict(title="Winter Relief", goal_amount="5000", start_date=TODAY, end_date=TODAY + timedelta(days=30))
    base.update(kw)
    return CampaignCreate(**base)


def test_new_campaign_starts_as_draft_and_defaults_manager(db, make_user):
    manager = make_user(Role.NGO_MANAGER)
    c = CampaignService(db).create(manager, payload())
    assert c.status == CampaignStatus.DRAFT and c.manager_id == manager.id and c.raised_amount == 0


def test_end_date_before_start_date_is_invalid():
    with pytest.raises(ValueError):
        payload(end_date=TODAY - timedelta(days=1))


def test_goal_must_be_positive():
    with pytest.raises(ValueError):
        payload(goal_amount="0")


def test_manager_must_be_privileged_user(db, make_user):
    admin = make_user(Role.SUPER_ADMIN)
    volunteer = make_user(Role.VOLUNTEER)
    with pytest.raises(BusinessRuleError):
        CampaignService(db).create(admin, payload(manager_id=volunteer.id))


def test_lifecycle_transitions(db, make_user):
    admin = make_user(Role.SUPER_ADMIN)
    svc = CampaignService(db)
    c = svc.create(admin, payload())
    assert svc.change_status(admin, c.id, CampaignStatus.ACTIVE).status == CampaignStatus.ACTIVE
    assert svc.change_status(admin, c.id, CampaignStatus.PAUSED).status == CampaignStatus.PAUSED
    assert svc.change_status(admin, c.id, CampaignStatus.ACTIVE).status == CampaignStatus.ACTIVE
    assert svc.change_status(admin, c.id, CampaignStatus.COMPLETED).status == CampaignStatus.COMPLETED


def test_invalid_transitions_are_rejected(db, make_user):
    admin = make_user(Role.SUPER_ADMIN)
    svc = CampaignService(db)
    draft = svc.create(admin, payload())
    with pytest.raises(BusinessRuleError):
        svc.change_status(admin, draft.id, CampaignStatus.PAUSED)  # draft cannot pause
    closed = mk_campaign(db, status=CampaignStatus.COMPLETED)
    with pytest.raises(BusinessRuleError):
        svc.change_status(admin, closed.id, CampaignStatus.ACTIVE)  # completed is terminal


def test_closed_campaign_cannot_be_edited(db, make_user):
    admin = make_user(Role.SUPER_ADMIN)
    closed = mk_campaign(db, status=CampaignStatus.CANCELLED)
    with pytest.raises(BusinessRuleError):
        CampaignService(db).update(admin, closed.id, CampaignUpdate(title="New title"))


def test_cannot_activate_expired_campaign(db, make_user):
    admin = make_user(Role.SUPER_ADMIN)
    old = mk_campaign(db, status=CampaignStatus.DRAFT, start_date=TODAY - timedelta(days=60), end_date=TODAY - timedelta(days=1))
    with pytest.raises(BusinessRuleError):
        CampaignService(db).change_status(admin, old.id, CampaignStatus.ACTIVE)


def test_public_roles_only_see_active_campaigns(db, make_user):
    donor_user = make_user(Role.DONOR)
    draft = mk_campaign(db, status=CampaignStatus.DRAFT)
    with pytest.raises(NotFoundError):
        CampaignService(db).get_for_actor(donor_user, draft.id)


def test_serialize_reports_goal_achievement(db):
    c = mk_campaign(db, goal="1000.00", raised="250.00")
    out = CampaignService.serialize(c)
    assert out.achievement_pct == 25.0 and str(out.remaining_amount) == "750.00"
