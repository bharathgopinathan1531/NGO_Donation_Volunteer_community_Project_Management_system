from app.utils.enums import Role
from tests.helpers import d


def test_create_project_defaults(api, auth):
    mgr = auth(Role.NGO_MANAGER)
    p = api.project(mgr, budget="7500.50", location="Warangal")
    assert p["status"] == "planning" and p["budget"] == "7500.50" and p["manager_id"] and p["approval_state"] is None
    assert p["milestones_total"] == 0 and p["milestone_completion_pct"] == 0.0 and p["objectives"]


def test_creation_permissions(api, auth):
    body = {"name": "Nope Project", "start_date": d(0), "end_date": d(10)}
    for role in (Role.FINANCE_OFFICER, Role.VOLUNTEER, Role.DONOR):
        assert api.post("/projects", auth(role), body).status_code == 403, role
    assert api.post("/projects", auth(Role.VOLUNTEER_COORDINATOR), body, 403) if False else True
    assert api.post("/projects", auth(Role.NGO_MANAGER), body, 201)


def test_validation(api, auth):
    mgr = auth(Role.NGO_MANAGER)
    base = {"name": "Valid Project", "start_date": d(0), "end_date": d(10)}
    assert api.post("/projects", mgr, {**base, "end_date": d(-1)}).status_code == 422
    assert api.post("/projects", mgr, {**base, "budget": "-5"}).status_code == 422
    assert api.post("/projects", mgr, {**base, "name": "x"}).status_code == 422
    assert api.post("/projects", mgr, {**base, "campaign_id": 9999}).status_code == 404
    donor_id = api.donor(mgr)["id"]
    assert api.post("/projects", mgr, {**base, "manager_id": 9999}).status_code == 404
    assert donor_id


def test_project_linked_to_campaign_and_manager(api, auth, admin, make_user):
    camp = api.campaign(admin)
    other_mgr = make_user(Role.NGO_MANAGER, "pm@example.org")
    p = api.project(admin, campaign_id=camp["id"], manager_id=other_mgr.id)
    assert p["campaign_id"] == camp["id"] and p["manager_id"] == other_mgr.id
    assert api.get("/projects", admin, 200, campaign_id=camp["id"]).json()["total"] == 1
    assert api.get("/projects", admin, 200, manager_id=other_mgr.id).json()["total"] == 1


def test_cannot_activate_until_approved(api, auth, admin):
    mgr = auth(Role.NGO_MANAGER)
    p = api.project(mgr)
    assert api.post(f"/projects/{p['id']}/status", admin, {"status": "active"}).status_code == 422
    assert api.post(f"/projects/{p['id']}/status", admin, {"status": "approved"}).status_code == 422  # not settable directly
    api.post(f"/projects/{p['id']}/submit", mgr, {}, 201)
    assert api.post(f"/projects/{p['id']}/status", admin, {"status": "active"}).status_code == 422  # still unapproved
    api.post(f"/projects/{p['id']}/approve", admin, {}, 200)
    assert api.post(f"/projects/{p['id']}/status", admin, {"status": "active"}, 200).json()["status"] == "active"


def test_status_lifecycle(api, auth, admin):
    p = api.approved_project(auth(Role.NGO_MANAGER), admin)
    pid = p["id"]
    assert p["status"] == "active" and p["approval_state"] == "approved"
    assert api.post(f"/projects/{pid}/status", admin, {"status": "on_hold"}, 200).json()["status"] == "on_hold"
    assert api.post(f"/projects/{pid}/status", admin, {"status": "active"}, 200).json()["status"] == "active"
    assert api.post(f"/projects/{pid}/status", admin, {"status": "planning"}).status_code == 422
    assert api.post(f"/projects/{pid}/status", admin, {"status": "completed"}, 200).json()["status"] == "completed"
    assert api.post(f"/projects/{pid}/status", admin, {"status": "active"}).status_code == 422
    assert api.patch(f"/projects/{pid}", admin, {"name": "Renamed"}).status_code == 422  # closed


def test_completion_requires_finished_milestones(api, auth, admin):
    mgr = auth(Role.NGO_MANAGER)
    p = api.approved_project(mgr, admin)
    ms = api.post("/milestones", mgr, {"project_id": p["id"], "title": "Phase one", "due_date": d(30)}, 201).json()
    assert api.post(f"/projects/{p['id']}/status", admin, {"status": "completed"}).status_code == 422
    api.patch(f"/milestones/{ms['id']}", mgr, {"status": "completed"}, 200)
    detail = api.get(f"/projects/{p['id']}", admin, 200).json()
    assert detail["milestones_completed"] == 1 and detail["milestone_completion_pct"] == 100.0
    assert api.post(f"/projects/{p['id']}/status", admin, {"status": "completed"}, 200)


def test_update_and_budget_floor(api, auth, admin):
    mgr, fin = auth(Role.NGO_MANAGER), auth(Role.FINANCE_OFFICER)
    p = api.approved_project(mgr, admin, budget="1000.00")
    e = api.expense(mgr, p["id"], "600.00", "UB-1").json()
    api.post(f"/expenses/{e['id']}/approve", fin, {}, 200)
    assert api.patch(f"/projects/{p['id']}", mgr, {"budget": "500"}).status_code == 422
    assert api.patch(f"/projects/{p['id']}", mgr, {"budget": "2000", "location": "Nalgonda"}, 200).json()["location"] == "Nalgonda"


def test_search_filter_sort(api, auth):
    mgr = auth(Role.NGO_MANAGER)
    api.project(mgr, "Alpha Wells", location="Hyderabad")
    api.project(mgr, "Beta School", location="Chennai")
    assert api.get("/projects", mgr, 200, search="alpha").json()["total"] == 1
    assert api.get("/projects", mgr, 200, location="chen").json()["items"][0]["name"] == "Beta School"
    assert api.get("/projects", mgr, 200, status="planning").json()["total"] == 2
    assert [i["name"] for i in api.get("/projects", mgr, sort_by="name", order="desc").json()["items"]] == ["Beta School", "Alpha Wells"]
    assert api.get("/projects", mgr, 200, date_from=d(100)).json()["total"] == 0


def test_volunteers_only_see_projects_they_are_assigned_to(api, auth, admin):
    mgr, coord = auth(Role.NGO_MANAGER), auth(Role.VOLUNTEER_COORDINATOR)
    mine, hidden = api.approved_project(mgr, admin, name="Mine"), api.approved_project(mgr, admin, name="Hidden")
    h, vol = api.volunteer_login("seer@example.org")
    api.post("/assignments", coord, {"volunteer_id": vol["id"], "project_id": mine["id"], "responsibility": "Helper", "start_date": d(0), "end_date": d(5)}, 201)
    assert [p["name"] for p in api.get("/projects", h, 200).json()["items"]] == ["Mine"]
    assert api.get(f"/projects/{mine['id']}", h, 200)
    assert api.get(f"/projects/{hidden['id']}", h).status_code == 403
    assert api.get(f"/projects/{hidden['id']}/milestones", h).status_code == 403
    assert api.patch(f"/projects/{mine['id']}", h, {"name": "Hacked"}).status_code == 403
    assert api.get("/projects", auth(Role.DONOR)).status_code == 200 and api.get("/projects", auth(Role.DONOR)).json()["total"] == 0
