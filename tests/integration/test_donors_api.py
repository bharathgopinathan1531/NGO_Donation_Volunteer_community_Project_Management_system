from app.utils.enums import Role
from tests.helpers import d


def test_donor_information_requires_permission(api, auth):
    donor = api.donor(auth(Role.NGO_MANAGER))
    for role in (Role.VOLUNTEER, Role.DONOR, Role.VOLUNTEER_COORDINATOR):
        assert api.get("/donors", auth(role)).status_code == 403, role
    assert api.get(f"/donors/{donor['id']}", auth(Role.VOLUNTEER)).status_code == 403
    assert api.post("/donors", auth(Role.FINANCE_OFFICER), {"name": "No Rights"}).status_code == 403  # finance reads only
    assert api.get("/donors", auth(Role.FINANCE_OFFICER)).status_code == 200


def test_create_organization_donor_and_duplicate_email(api, auth):
    h = auth(Role.NGO_MANAGER)
    r = api.post("/donors", h, {"name": "Acme Corp", "donor_type": "organization", "email": "Hello@Acme.org", "contact_person": "Jo", "phone": "+91 98765 43210"}, 201).json()
    assert r["donor_type"] == "organization" and r["status"] == "active" and r["email"] == "hello@acme.org"
    assert api.post("/donors", h, {"name": "Other", "email": "hello@acme.org"}).status_code == 409
    assert api.post("/donors", h, {"name": "Bad Phone", "phone": "call me"}).status_code == 422
    assert api.post("/donors", h, {"name": "X", "donor_type": "alien"}).status_code == 422


def test_search_filter_sort_paginate(api, auth):
    h = auth(Role.NGO_MANAGER)
    api.donor(h, "Alice", "a@example.org", city="Delhi")
    api.donor(h, "Bob", "b@example.org", city="Mumbai", donor_type="organization")
    api.donor(h, "Carol", "c@example.org", city="Delhi")
    assert api.get("/donors", h, search="ali").json()["total"] == 1
    assert api.get("/donors", h, city="Delhi").json()["total"] == 2
    assert api.get("/donors", h, donor_type="organization").json()["items"][0]["name"] == "Bob"
    page = api.get("/donors", h, page_size=2, sort_by="name", order="desc").json()
    assert [i["name"] for i in page["items"]] == ["Carol", "Bob"] and page["pages"] == 2 and page["total"] == 3
    assert api.get("/donors", h, sort_by="password").status_code == 400
    assert api.get("/donors", h, page=0).status_code == 422


def test_update_and_status(api, auth):
    h = auth(Role.NGO_MANAGER)
    donor = api.donor(h)
    r = api.patch(f"/donors/{donor['id']}", h, {"city": "Pune", "status": "inactive"}, 200).json()
    assert r["city"] == "Pune" and r["status"] == "inactive"
    assert api.patch("/donors/999", h, {"city": "x"}).status_code == 404


def test_donor_user_sees_only_their_own_profile_and_history(api, auth):
    mgr = auth(Role.NGO_MANAGER)
    me = api.signup("donor@example.org", "donor")
    other = api.donor(mgr, "Someone Else", "else@example.org")
    mine = api.get("/donors/me", me, 200).json()
    assert mine["email"] == "donor@example.org"
    assert api.get(f"/donors/{mine['id']}", me, 200)
    assert api.get(f"/donors/{other['id']}", me).status_code == 403
    assert api.get(f"/donors/{other['id']}/donations", me).status_code == 403
    assert api.get("/donors/me", auth(Role.NGO_MANAGER)).status_code == 403


def test_registering_donor_links_existing_staff_created_profile(api, auth):
    existing = api.donor(auth(Role.NGO_MANAGER), "Prior Donor", "prior@example.org")
    me = api.signup("prior@example.org", "donor")
    assert api.get("/donors/me", me, 200).json()["id"] == existing["id"]


def test_donation_history_of_a_donor(api, auth, admin):
    donor = api.donor(admin)
    camp = api.campaign(admin)
    api.donation(admin, donor["id"], camp["id"], "100", "H-1").json()
    api.donation(admin, donor["id"], camp["id"], "200", "H-2", status="pending")
    page = api.get(f"/donors/{donor['id']}/donations", admin, 200).json()
    assert page["total"] == 2
    assert api.get(f"/donors/{donor['id']}/donations", admin, 200, status="confirmed").json()["total"] == 1
    assert api.get(f"/donors/{donor['id']}/donations", admin, 200, date_from=d(5)).json()["total"] == 0
