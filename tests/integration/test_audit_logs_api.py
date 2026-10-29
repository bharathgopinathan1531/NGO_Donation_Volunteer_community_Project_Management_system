from app.utils.enums import Role
from tests.helpers import d


def test_actions_are_audited_with_actor(api, auth, admin):
    mgr = auth(Role.NGO_MANAGER)
    p = api.project(mgr)
    logs = api.get("/audit-logs", admin, 200, entity="project").json()
    assert logs["total"] >= 1
    row = logs["items"][0]
    assert row["actor_id"] and row["action"] and row["entity"] == "project" and row["entity_id"] == p["id"] and row["created_at"]
    assert api.get(f"/audit-logs/{row['id']}", admin, 200).json()["id"] == row["id"]
    assert api.get("/audit-logs/999999", admin).status_code == 404


def test_login_and_financial_actions_logged_and_filterable(api, auth, admin):
    mgr, fin = auth(Role.NGO_MANAGER), auth(Role.FINANCE_OFFICER)
    p = api.approved_project(mgr, admin)
    e = api.expense(mgr, p["id"], "10.00", "AU-1").json()
    api.post(f"/expenses/{e['id']}/approve", fin, {}, 200)
    acts = {i["action"] for i in api.get("/audit-logs", admin, 200, page_size=100).json()["items"]}
    assert any("expense" in a and "approve" in a for a in acts) and any("login" in a for a in acts)
    assert api.get("/audit-logs", admin, 200, entity="expense", entity_id=e["id"]).json()["total"] >= 2
    assert api.get("/audit-logs", admin, 200, date_from=d(1)).json()["total"] == 0


def test_denied_mutations_are_recorded_by_middleware(api, auth, admin):
    vol = auth(Role.VOLUNTEER)
    assert api.post("/projects", vol, {"name": "Sneaky Project", "start_date": d(0), "end_date": d(5)}).status_code == 403
    r = api.c.post("/api/v1/projects", json={"name": "Anon Project"})
    assert r.status_code == 401
    denied = api.get("/audit-logs", admin, 200, action="security.access_denied").json()
    assert denied["total"] >= 2


def test_audit_access_is_restricted(api, auth):
    for role in (Role.VOLUNTEER, Role.DONOR, Role.FINANCE_OFFICER, Role.VOLUNTEER_COORDINATOR):
        assert api.get("/audit-logs", auth(role)).status_code == 403, role
    assert api.get("/audit-logs", auth(Role.NGO_MANAGER)).status_code == 200
