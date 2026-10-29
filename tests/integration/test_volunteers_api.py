from app.utils.enums import Role


def test_staff_register_volunteer_with_full_profile(api, auth):
    h = auth(Role.VOLUNTEER_COORDINATOR)
    v = api.post("/volunteers", h, {
        "full_name": "Anita Desai", "email": "Anita@Example.org", "phone": "+91 99999 12345", "skills": ["Teaching", "teaching", "Driving"],
        "experience": "3 years at a food bank", "availability": "weekends",
        "emergency_contact_name": "Raj Desai", "emergency_contact_phone": "9876500000", "emergency_contact_relation": "brother",
    }, 201).json()
    assert v["email"] == "anita@example.org" and v["skills"] == ["Teaching", "Driving"] and v["status"] == "active"
    assert v["emergency_contact_name"] == "Raj Desai" and v["availability"] == "weekends"


def test_duplicate_and_invalid_input(api, auth):
    h = auth(Role.NGO_MANAGER)
    api.volunteer(h, email="same@example.org")
    assert api.post("/volunteers", h, {"full_name": "Other", "email": "same@example.org"}).status_code == 409
    assert api.post("/volunteers", h, {"full_name": "Bad", "email": "nope"}).status_code == 422
    assert api.post("/volunteers", h, {"full_name": "Bad", "email": "b@example.org", "phone": "xx"}).status_code == 422


def test_search_and_filtering(api, auth):
    h = auth(Role.VOLUNTEER_COORDINATOR)
    api.volunteer(h, "Cook Carl", "carl@example.org", skills=["cooking"], availability="weekday evenings")
    b = api.volunteer(h, "Driver Dan", "dan@example.org", skills=["driving"])
    api.patch(f"/volunteers/{b['id']}", h, {"status": "on_leave"}, 200)
    assert api.get("/volunteers", h, skill="cook").json()["total"] == 1
    assert api.get("/volunteers", h, search="dan").json()["items"][0]["full_name"] == "Driver Dan"
    assert api.get("/volunteers", h, status="on_leave").json()["total"] == 1
    assert api.get("/volunteers", h, availability="evenings").json()["total"] == 1


def test_self_registration_flow(api, auth):
    h, profile = api.volunteer_login("self@example.org")
    assert profile["user_id"] and profile["email"] == "self@example.org"
    assert api.get("/volunteers/me", h, 200).json()["id"] == profile["id"]
    assert api.post("/volunteers/me", h, {"full_name": "Again", "email": "self@example.org"}).status_code == 409
    upd = api.patch(f"/volunteers/{profile['id']}", h, {"availability": "mornings", "skills": ["gardening"]}, 200).json()
    assert upd["availability"] == "mornings" and upd["skills"] == ["gardening"]
    assert api.patch(f"/volunteers/{profile['id']}", h, {"status": "active"}).status_code == 403


def test_self_registration_email_must_match_account(api):
    h = api.signup("a@example.org", "volunteer")
    assert api.post("/volunteers/me", h, {"full_name": "Imposter", "email": "b@example.org"}).status_code == 422


def test_access_control(api, auth):
    mgr = auth(Role.NGO_MANAGER)
    vol = api.volunteer(mgr)
    h1, mine = api.volunteer_login("v1@example.org")
    assert api.get("/volunteers", h1).status_code == 403  # a volunteer cannot browse the roster
    assert api.get(f"/volunteers/{vol['id']}", h1).status_code == 403
    assert api.get(f"/volunteers/{mine['id']}", h1).status_code == 200
    assert api.patch(f"/volunteers/{vol['id']}", h1, {"availability": "hacked"}).status_code == 403
    assert api.post("/volunteers", h1, {"full_name": "X Y", "email": "z@example.org"}).status_code == 403
    assert api.post("/volunteers", auth(Role.FINANCE_OFFICER), {"full_name": "X Y", "email": "z@example.org"}).status_code == 403
    assert api.get("/volunteers/me", auth(Role.NGO_MANAGER)).status_code == 404  # staff without a profile


def test_donor_cannot_self_register_as_volunteer(api):
    h = api.signup("don@example.org", "donor")
    assert api.post("/volunteers/me", h, {"full_name": "Don Or", "email": "don@example.org"}).status_code == 403
