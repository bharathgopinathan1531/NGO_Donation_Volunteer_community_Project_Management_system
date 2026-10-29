from app.utils.enums import Role


def test_submit_and_summarise(api, auth, admin):
    mgr = auth(Role.NGO_MANAGER)
    p1, p2 = api.approved_project(mgr, admin, name="Impact One"), api.approved_project(mgr, admin, name="Impact Two")
    api.post("/impact/updates", mgr, {"project_id": p1["id"], "beneficiaries_served": 40, "volunteer_hours": "12.5", "resources_distributed": 30, "funds_utilized": "900.00", "milestones_achieved": 2}, 201)
    api.post("/impact/updates", mgr, {"project_id": p1["id"], "beneficiaries_served": 10}, 201)
    api.post("/impact/updates", mgr, {"project_id": p2["id"], "beneficiaries_served": 5, "notes": "first"}, 201)
    hist = api.get("/impact/updates", mgr, 200, project_id=p1["id"]).json()
    assert hist["total"] == 2 and {i["beneficiaries_served"] for i in hist["items"]} == {40, 10}
    first = next(i for i in hist["items"] if i["beneficiaries_served"] == 40)
    assert first["volunteer_hours"] == "12.50" and first["funds_utilized"] == "900.00" and first["submitted_by"]
    # the summary is computed live from database records, not from the submitted figures
    assert api.get("/impact/summary", mgr, 200, project_id=p1["id"]).json()["project_id"] == p1["id"]
    assert api.get("/impact/summary", mgr, 200).json()["projects_completed"] == 0
    assert api.get("/impact/summary", mgr, project_id=9999).status_code == 404
    assert api.get("/impact/updates", mgr, 200, project_id=p2["id"]).json()["total"] == 1


def test_validation_and_permissions(api, auth, admin):
    mgr = auth(Role.NGO_MANAGER)
    p = api.approved_project(mgr, admin)
    assert api.post("/impact/updates", mgr, {"project_id": p["id"], "beneficiaries_served": -1}).status_code == 422
    assert api.post("/impact/updates", mgr, {"project_id": 9999}).status_code == 404
    for role in (Role.VOLUNTEER, Role.DONOR, Role.FINANCE_OFFICER):
        assert api.post("/impact/updates", auth(role), {"project_id": p["id"]}).status_code == 403, role
    assert api.get("/impact/summary", auth(Role.FINANCE_OFFICER)).status_code == 200
    assert api.get("/impact/summary", auth(Role.DONOR)).status_code == 403
