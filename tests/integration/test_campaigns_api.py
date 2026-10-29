from app.utils.enums import Role
from tests.helpers import d


def test_create_defaults_and_manager_assignment(api, auth, make_user):
    mgr = auth(Role.NGO_MANAGER)
    c = api.campaign(mgr, activate=False)
    assert c["status"] == "draft" and c["raised_amount"] == "0.00" and c["achievement_pct"] == 0.0 and c["manager_id"]
    other = make_user(Role.NGO_MANAGER, "m2@example.org")
    assert api.campaign(mgr, "Assigned", activate=False, manager_id=other.id)["manager_id"] == other.id


def test_only_authorised_roles_create_campaigns(api, auth):
    body = {"title": "Nope", "goal_amount": "10", "start_date": d(0), "end_date": d(5)}
    for role in (Role.FINANCE_OFFICER, Role.VOLUNTEER_COORDINATOR, Role.VOLUNTEER, Role.DONOR):
        assert api.post("/campaigns", auth(role), body).status_code == 403, role
    assert api.post("/campaigns", None, body).status_code == 401


def test_validation(api, auth):
    h = auth(Role.NGO_MANAGER)
    base = {"title": "Valid title", "goal_amount": "100", "start_date": d(0), "end_date": d(5)}
    assert api.post("/campaigns", h, {**base, "goal_amount": "0"}).status_code == 422
    assert api.post("/campaigns", h, {**base, "goal_amount": "-1"}).status_code == 422
    assert api.post("/campaigns", h, {**base, "end_date": d(-1)}).status_code == 422
    assert api.post("/campaigns", h, {**base, "category": "bogus"}).status_code == 422
    assert api.post("/campaigns", h, {**base, "manager_id": 9999}).status_code == 404


def test_activate_pause_resume_close(api, auth):
    h = auth(Role.NGO_MANAGER)
    c = api.campaign(h, activate=False)
    cid = c["id"]
    assert api.post(f"/campaigns/{cid}/pause", h).status_code == 422  # draft cannot pause
    assert api.post(f"/campaigns/{cid}/activate", h, expect=200).json()["status"] == "active"
    assert api.post(f"/campaigns/{cid}/pause", h, expect=200).json()["status"] == "paused"
    assert api.post(f"/campaigns/{cid}/activate", h, expect=200).json()["status"] == "active"
    assert api.post(f"/campaigns/{cid}/close", h, expect=200).json()["status"] == "completed"
    assert api.post(f"/campaigns/{cid}/activate", h).status_code == 422  # terminal
    assert api.patch(f"/campaigns/{cid}", h, {"title": "Changed"}).status_code == 422


def test_cancel_from_draft(api, auth):
    h = auth(Role.NGO_MANAGER)
    c = api.campaign(h, activate=False)
    assert api.post(f"/campaigns/{c['id']}/cancel", h, expect=200).json()["status"] == "cancelled"


def test_update_fields(api, auth):
    h = auth(Role.NGO_MANAGER)
    c = api.campaign(h, goal="1000.00")
    r = api.patch(f"/campaigns/{c['id']}", h, {"goal_amount": "2500.00", "title": "Bigger goal"}, 200).json()
    assert r["goal_amount"] == "2500.00" and r["title"] == "Bigger goal"
    assert api.patch(f"/campaigns/{c['id']}", h, {"end_date": d(-100)}).status_code == 422
    assert api.patch(f"/campaigns/{c['id']}", h, {"goal_amount": None}).status_code in (200, 422)


def test_filters_search_sort(api, auth):
    h = auth(Role.NGO_MANAGER)
    api.campaign(h, "Education Fund", category="education")
    api.campaign(h, "Health Camp", category="health", activate=False)
    assert api.get("/campaigns", h, 200, category="education").json()["total"] == 1
    assert api.get("/campaigns", h, 200, status="draft").json()["items"][0]["title"] == "Health Camp"
    assert api.get("/campaigns", h, 200, search="fund").json()["total"] == 1
    assert [i["title"] for i in api.get("/campaigns", h, sort_by="title", order="desc").json()["items"]] == ["Health Camp", "Education Fund"]


def test_donors_and_volunteers_see_only_active_campaigns(api, auth):
    mgr = auth(Role.NGO_MANAGER)
    live = api.campaign(mgr, "Live")
    draft = api.campaign(mgr, "Draft", activate=False)
    donor = api.signup("d@example.org", "donor")
    page = api.get("/campaigns", donor, 200).json()
    assert [c["id"] for c in page["items"]] == [live["id"]]
    assert api.get(f"/campaigns/{draft['id']}", donor).status_code == 404
    assert api.get(f"/campaigns/{live['id']}", donor).status_code == 200
    assert api.post(f"/campaigns/{live['id']}/pause", donor).status_code == 403


def test_goal_achievement_is_reported(api, auth, admin):
    c = api.campaign(admin, goal="1000.00")
    donor = api.donor(admin)
    api.donation(admin, donor["id"], c["id"], "250.00", "G-1", expect=None)
    got = api.get(f"/campaigns/{c['id']}", admin, 200).json()
    assert got["raised_amount"] == "250.00" and got["achievement_pct"] == 25.0 and got["remaining_amount"] == "750.00"
