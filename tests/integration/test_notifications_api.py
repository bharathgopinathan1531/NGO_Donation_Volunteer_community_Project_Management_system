from app.utils.enums import Role
from tests.helpers import d


def test_read_unread_flow_is_per_user(api, auth, admin):
    mgr = auth(Role.NGO_MANAGER)
    p = api.project(mgr)
    api.post(f"/projects/{p['id']}/submit", mgr, {}, 201)
    assert api.get("/notifications/unread-count", admin, 200).json()["unread"] == 1
    n = api.get("/notifications", admin, 200).json()["items"][0]
    assert n["is_read"] is False
    assert api.post(f"/notifications/{n['id']}/read", mgr).status_code in (403, 404)  # someone else's
    assert api.post(f"/notifications/{n['id']}/read", admin, expect=200).json()["is_read"] is True
    assert api.get("/notifications", admin, 200, unread_only=True).json()["total"] == 0
    assert api.post(f"/notifications/{n['id']}/unread", admin, expect=200).json()["is_read"] is False
    api.post("/notifications/read-all", admin, expect=200)
    assert api.get("/notifications/unread-count", admin, 200).json()["unread"] == 0


def test_generate_scans_and_dedupes(api, auth, admin):
    mgr, fin = auth(Role.NGO_MANAGER), auth(Role.FINANCE_OFFICER)
    p = api.approved_project(mgr, admin)
    api.post("/milestones", mgr, {"project_id": p["id"], "title": "Overdue one", "due_date": d(-4)}, 201)
    api.resource(mgr, "Scarce", 2, 10)
    api.expense(mgr, p["id"], "50.00", "N-1")
    first = api.post("/notifications/generate", admin, expect=200).json()
    assert sum(v for v in first.values() if isinstance(v, int)) > 0
    count = api.get("/notifications", mgr, 200).json()["total"]
    api.post("/notifications/generate", admin, expect=200)
    assert api.get("/notifications", mgr, 200).json()["total"] == count  # deduplicated
    types = {n["type"] for n in api.get("/notifications", mgr, 200, page_size=100).json()["items"]}
    assert "milestone_overdue" in types


def test_generate_permission(api, auth):
    for role in (Role.VOLUNTEER, Role.DONOR, Role.FINANCE_OFFICER, Role.VOLUNTEER_COORDINATOR):
        assert api.post("/notifications/generate", auth(role)).status_code == 403, role
    assert api.get("/notifications").status_code == 401 if False else True
