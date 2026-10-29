from app.utils.enums import Role


def test_set_and_replace_project_budget(api, auth, admin):
    fin, mgr = auth(Role.FINANCE_OFFICER), auth(Role.NGO_MANAGER)
    p = api.approved_project(mgr, admin, budget="1000.00")
    r = api.put("/budgets", fin, {"scope": "project", "project_id": p["id"], "amount": "2500.00"}, 200).json()
    assert r["amount"] == "2500.00" and r["project_id"] == p["id"]
    api.put("/budgets", fin, {"scope": "project", "project_id": p["id"], "amount": "3000.00"}, 200)
    assert api.get("/budgets", fin, 200).json()["total"] == 1  # replaced, not duplicated
    assert api.get(f"/budgets/projects/{p['id']}/utilization", fin, 200).json()["budget"] == "3000.00"


def test_campaign_budget_and_validation(api, auth, admin):
    fin = auth(Role.FINANCE_OFFICER)
    c = api.campaign(admin)
    api.put("/budgets", fin, {"scope": "campaign", "campaign_id": c["id"], "amount": "800"}, 200)
    u = api.get(f"/budgets/campaigns/{c['id']}/utilization", fin, 200).json()
    assert u["budget"] == "800.00" and u["spent"] == "0.00" and u["is_overrun"] is False
    assert api.put("/budgets", fin, {"scope": "campaign", "project_id": 1, "amount": "5"}).status_code == 422
    assert api.put("/budgets", fin, {"scope": "campaign", "campaign_id": c["id"], "amount": "-5"}).status_code == 422
    assert api.put("/budgets", fin, {"scope": "project", "project_id": 9999, "amount": "5"}).status_code == 404


def test_utilization_tracks_spent_pending_and_overruns(api, auth, admin):
    fin, mgr = auth(Role.FINANCE_OFFICER), auth(Role.NGO_MANAGER)
    p = api.approved_project(mgr, admin, budget="1000.00")
    e1 = api.expense(mgr, p["id"], "400.00", "U-1").json()
    api.expense(mgr, p["id"], "100.00", "U-2")
    api.post(f"/expenses/{e1['id']}/approve", fin, {}, 200)
    u = api.get(f"/budgets/projects/{p['id']}/utilization", fin, 200).json()
    assert (u["spent"], u["pending"], u["remaining"], u["utilization_pct"]) == ("400.00", "100.00", "600.00", 40.0)
    assert api.get("/budgets/utilization", fin, 200, only_overruns=True).json() == []
    assert len(api.get("/budgets/utilization", fin, 200, scope="project").json()) == 1


def test_permissions(api, auth, admin):
    p = api.approved_project(auth(Role.NGO_MANAGER), admin)
    body = {"scope": "project", "project_id": p["id"], "amount": "10"}
    for role in (Role.VOLUNTEER, Role.DONOR, Role.VOLUNTEER_COORDINATOR):
        assert api.put("/budgets", auth(role), body).status_code == 403, role
    assert api.get("/budgets", auth(Role.VOLUNTEER_COORDINATOR)).status_code == 403
