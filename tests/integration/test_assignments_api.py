from app.utils.enums import Role
from tests.helpers import d


def body(vol, project, a=0, b=10, role="Site helper"):
    return {"volunteer_id": vol["id"], "project_id": project["id"], "responsibility": role, "start_date": d(a), "end_date": d(b)}


def test_assign_volunteer_and_notify_them(api, auth, admin):
    coord = auth(Role.VOLUNTEER_COORDINATOR)
    vh, profile = api.volunteer_login("assignee@example.org")
    project = api.approved_project(auth(Role.NGO_MANAGER), admin)
    a = api.post("/assignments", coord, body(profile, project), 201).json()
    assert a["status"] == "assigned" and a["hours_completed"] == "0.00" and a["assigned_by"]
    notes = api.get("/notifications", vh, 200).json()
    assert notes["total"] == 1 and notes["items"][0]["type"] == "volunteer_assignment" and notes["items"][0]["is_read"] is False


def test_conflicting_assignments_prevented(api, auth, admin):
    coord, mgr = auth(Role.VOLUNTEER_COORDINATOR), auth(Role.NGO_MANAGER)
    vol = api.volunteer(coord)
    p1, p2 = api.approved_project(mgr, admin, name="P One"), api.approved_project(mgr, admin, name="P Two")
    first = api.post("/assignments", coord, body(vol, p1, 0, 10), 201).json()
    r = api.post("/assignments", coord, body(vol, p2, 5, 15))
    assert r.status_code == 409 and r.json()["error"]["conflicting_assignment_ids"] == [first["id"]]
    assert api.post("/assignments", coord, body(vol, p2, 11, 20)).status_code == 201  # next day is fine
    api.post(f"/assignments/{first['id']}/status", coord, {"status": "cancelled"}, 200)
    assert api.post("/assignments", coord, body(vol, p2, 0, 10)).status_code == 201  # cancellation frees the slot


def test_validation_rules(api, auth, admin):
    coord = auth(Role.VOLUNTEER_COORDINATOR)
    vol, project = api.volunteer(coord), api.approved_project(auth(Role.NGO_MANAGER), admin)
    assert api.post("/assignments", coord, body(vol, project, 10, 5)).status_code == 422
    assert api.post("/assignments", coord, body(vol, project, 0, 500)).status_code == 422  # beyond project end
    assert api.post("/assignments", coord, {**body(vol, project), "volunteer_id": 9999}).status_code == 404
    assert api.post("/assignments", coord, {**body(vol, project), "project_id": 9999}).status_code == 404
    api.patch(f"/volunteers/{vol['id']}", coord, {"status": "suspended"}, 200)
    assert api.post("/assignments", coord, body(vol, project)).status_code == 422


def test_cannot_assign_to_closed_project(api, auth, admin):
    coord = auth(Role.VOLUNTEER_COORDINATOR)
    vol, project = api.volunteer(coord), api.approved_project(auth(Role.NGO_MANAGER), admin)
    api.post(f"/projects/{project['id']}/status", admin, {"status": "cancelled"}, 200)
    assert api.post("/assignments", coord, body(vol, project)).status_code == 422


def test_status_lifecycle_and_history_retained(api, auth, admin):
    coord = auth(Role.VOLUNTEER_COORDINATOR)
    vol, project = api.volunteer(coord), api.approved_project(auth(Role.NGO_MANAGER), admin)
    a = api.post("/assignments", coord, body(vol, project), 201).json()
    assert api.post(f"/assignments/{a['id']}/status", coord, {"status": "completed"}).status_code == 422  # must be active first
    api.post(f"/assignments/{a['id']}/status", coord, {"status": "active"}, 200)
    api.post(f"/assignments/{a['id']}/status", coord, {"status": "completed"}, 200)
    assert api.patch(f"/assignments/{a['id']}", coord, {"responsibility": "Changed"}).status_code == 422
    history = api.get("/assignments", coord, 200, volunteer_id=vol["id"]).json()
    assert history["total"] == 1 and history["items"][0]["status"] == "completed"  # nothing is ever deleted


def test_update_dates_rechecks_conflicts(api, auth, admin):
    coord = auth(Role.VOLUNTEER_COORDINATOR)
    vol, project = api.volunteer(coord), api.approved_project(auth(Role.NGO_MANAGER), admin)
    api.post("/assignments", coord, body(vol, project, 0, 10), 201)
    second = api.post("/assignments", coord, body(vol, project, 11, 20), 201).json()
    assert api.patch(f"/assignments/{second['id']}", coord, {"start_date": d(5)}).status_code == 409
    assert api.patch(f"/assignments/{second['id']}", coord, {"end_date": d(25), "responsibility": "Lead"}, 200).json()["responsibility"] == "Lead"


def test_volunteers_see_only_their_own(api, auth, admin):
    coord, mgr = auth(Role.VOLUNTEER_COORDINATOR), auth(Role.NGO_MANAGER)
    project = api.approved_project(mgr, admin)
    h1, v1 = api.volunteer_login("v1@example.org")
    _, v2 = api.volunteer_login("v2@example.org")
    a1 = api.post("/assignments", coord, body(v1, project, 0, 5), 201).json()
    a2 = api.post("/assignments", coord, body(v2, project, 0, 5), 201).json()
    mine = api.get("/assignments", h1, 200).json()
    assert [i["id"] for i in mine["items"]] == [a1["id"]]
    assert api.get(f"/assignments/{a1['id']}", h1, 200)
    assert api.get(f"/assignments/{a2['id']}", h1).status_code == 403
    assert api.get("/assignments", h1, volunteer_id=v2["id"]).status_code == 403
    assert api.post("/assignments", h1, body(v1, project, 20, 25)).status_code == 403
    assert api.post(f"/assignments/{a1['id']}/status", h1, {"status": "active"}).status_code == 403


def test_other_staff_roles(api, auth, admin):
    coord = auth(Role.VOLUNTEER_COORDINATOR)
    vol, project = api.volunteer(coord), api.approved_project(auth(Role.NGO_MANAGER), admin)
    assert api.post("/assignments", auth(Role.FINANCE_OFFICER), body(vol, project)).status_code == 403
    assert api.post("/assignments", auth(Role.DONOR), body(vol, project)).status_code == 403
    assert api.post("/assignments", auth(Role.NGO_MANAGER), body(vol, project), 201)
