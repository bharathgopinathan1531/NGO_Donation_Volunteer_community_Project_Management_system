import pytest

from app.core.exceptions import BusinessRuleError, ConflictError, ForbiddenError
from app.schemas.volunteer import VolunteerCreate, VolunteerUpdate
from app.services.volunteer_service import VolunteerService, to_out
from app.utils.enums import Role, VolunteerStatus
from app.utils.pagination import PaginationParams
from app.utils.sorting import SortParams


def vc(email="v@example.org", **kw):
    return VolunteerCreate(full_name="Vol Unteer", email=email, **kw)


def test_register_normalises_and_dedupes_skills(db, make_user):
    admin = make_user(Role.VOLUNTEER_COORDINATOR)
    v = VolunteerService(db).create(admin, vc("V@Example.org", skills=["Teaching", " teaching ", "First Aid", ""]))
    assert v.email == "v@example.org" and to_out(v).skills == ["Teaching", "First Aid"]


def test_duplicate_email_conflicts(db, make_user):
    admin = make_user(Role.VOLUNTEER_COORDINATOR)
    VolunteerService(db).create(admin, vc())
    with pytest.raises(ConflictError):
        VolunteerService(db).create(admin, vc())


def test_emergency_contact_is_stored(db, make_user):
    admin = make_user(Role.VOLUNTEER_COORDINATOR)
    v = VolunteerService(db).create(admin, vc(emergency_contact_name="Mum", emergency_contact_phone="9876543210", emergency_contact_relation="mother"))
    assert (v.emergency_contact_name, v.emergency_contact_phone) == ("Mum", "9876543210")


def test_invalid_phone_rejected_by_schema():
    with pytest.raises(ValueError):
        vc(phone="abc")


def test_self_registration_requires_matching_email_and_one_profile(db, make_user):
    user = make_user(Role.VOLUNTEER, "me@example.org")
    svc = VolunteerService(db)
    with pytest.raises(BusinessRuleError):
        svc.register_self(user, vc("someone-else@example.org"))
    v = svc.register_self(user, vc("me@example.org"))
    assert v.user_id == user.id
    with pytest.raises(ConflictError):
        svc.register_self(user, vc("me@example.org"))


def test_non_volunteer_cannot_self_register(db, make_user):
    donor = make_user(Role.DONOR)
    with pytest.raises(ForbiddenError):
        VolunteerService(db).register_self(donor, vc(donor.email))


def test_volunteer_may_edit_own_profile_but_not_status_or_others(db, make_user):
    user = make_user(Role.VOLUNTEER, "me@example.org")
    other = make_user(Role.VOLUNTEER, "other@example.org")
    svc = VolunteerService(db)
    mine = svc.register_self(user, vc("me@example.org"))
    theirs = svc.register_self(other, vc("other@example.org"))
    assert svc.update(user, mine.id, VolunteerUpdate(availability="evenings")).availability == "evenings"
    with pytest.raises(ForbiddenError):
        svc.update(user, mine.id, VolunteerUpdate(status=VolunteerStatus.ACTIVE))
    with pytest.raises(ForbiddenError):
        svc.update(user, theirs.id, VolunteerUpdate(availability="x"))


def test_search_by_skill_and_status(db, make_user):
    admin = make_user(Role.VOLUNTEER_COORDINATOR)
    svc = VolunteerService(db)
    svc.create(admin, vc("a@example.org", skills=["cooking"]))
    b = svc.create(admin, vc("b@example.org", skills=["driving"]))
    svc.update(admin, b.id, VolunteerUpdate(status=VolunteerStatus.ON_LEAVE))
    p, s = PaginationParams(), SortParams()
    items, _ = svc.list_volunteers(p, s, search=None, status=None, skill="cook", availability=None)
    assert [i.email for i in items] == ["a@example.org"]
    items, _ = svc.list_volunteers(p, s, search=None, status=VolunteerStatus.ON_LEAVE, skill=None, availability=None)
    assert [i.email for i in items] == ["b@example.org"]
