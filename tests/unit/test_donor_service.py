import pytest

from app.core.exceptions import ConflictError, ForbiddenError
from app.schemas.donor import DonorCreate, DonorUpdate
from app.services.donor_service import DonorService
from app.utils.enums import DonorStatus, DonorType, Role
from app.utils.pagination import PaginationParams
from app.utils.sorting import SortParams
from tests.unit.factories import mk_donor


def test_create_and_update_donor(db, make_user):
    admin = make_user(Role.SUPER_ADMIN)
    svc = DonorService(db)
    donor = svc.create(admin, DonorCreate(name="Acme Foundation", donor_type=DonorType.ORGANIZATION, email="Info@Acme.org", contact_person="Jo"))
    assert donor.email == "info@acme.org" and donor.status == DonorStatus.ACTIVE
    svc.update(admin, donor.id, DonorUpdate(city="Pune", status=DonorStatus.INACTIVE))
    assert donor.city == "Pune" and donor.status == DonorStatus.INACTIVE


def test_duplicate_donor_email_rejected(db, make_user):
    admin = make_user(Role.SUPER_ADMIN)
    DonorService(db).create(admin, DonorCreate(name="A Donor", email="same@example.org"))
    with pytest.raises(ConflictError):
        DonorService(db).create(admin, DonorCreate(name="B Donor", email="same@example.org"))


def test_donor_user_can_only_see_own_profile(db, make_user):
    donor_user = make_user(Role.DONOR, "d1@example.org")
    mine = mk_donor(db, "Mine", "mine@example.org", user_id=donor_user.id)
    other = mk_donor(db, "Other", "other@example.org")
    svc = DonorService(db)
    assert svc.get_for_actor(donor_user, mine.id).id == mine.id
    with pytest.raises(ForbiddenError):
        svc.get_for_actor(donor_user, other.id)


def test_volunteer_cannot_read_donor_information(db, make_user):
    volunteer = make_user(Role.VOLUNTEER)
    donor = mk_donor(db)
    with pytest.raises(ForbiddenError):
        DonorService(db).get_for_actor(volunteer, donor.id)


def test_search_and_filter(db):
    mk_donor(db, "Alice Smith", "alice@example.org", city="Delhi")
    mk_donor(db, "Bob Org", "bob@example.org", donor_type=DonorType.ORGANIZATION, city="Mumbai")
    svc = DonorService(db)
    p, s = PaginationParams(), SortParams()
    items, total = svc.list_donors(p, s, search="alice", donor_type=None, status=None, city=None, country=None)
    assert total == 1 and items[0].name == "Alice Smith"
    items, total = svc.list_donors(p, s, search=None, donor_type=DonorType.ORGANIZATION, status=None, city=None, country=None)
    assert [i.name for i in items] == ["Bob Org"]
