from app.utils.enums import Role


def test_allocation_reduces_stock_and_is_listed(api, auth, admin):
    mgr = auth(Role.NGO_MANAGER)
    p = api.approved_project(mgr, admin)
    r = api.resource(mgr, "Tents", 40, 5)
    a = api.post("/resource-allocations", mgr, {"resource_id": r["id"], "project_id": p["id"], "quantity": 15}, 201).json()
    assert a["quantity"] == 15 and a["allocated_by"]
    assert api.get(f"/resources/{r['id']}", mgr, 200).json()["quantity"] == 25
    assert api.get("/resource-allocations", mgr, 200, project_id=p["id"]).json()["total"] == 1
    assert api.get("/resources/transactions", mgr, 200, project_id=p["id"]).json()["total"] == 1


def test_cannot_over_allocate_or_use_bad_targets(api, auth, admin):
    mgr = auth(Role.NGO_MANAGER)
    p = api.approved_project(mgr, admin)
    r = api.resource(mgr, "Tents", 10, 1)
    assert api.post("/resource-allocations", mgr, {"resource_id": r["id"], "project_id": p["id"], "quantity": 11}).status_code == 422
    assert api.post("/resource-allocations", mgr, {"resource_id": r["id"], "project_id": p["id"], "quantity": 0}).status_code == 422
    assert api.post("/resource-allocations", mgr, {"resource_id": 9999, "project_id": p["id"], "quantity": 1}).status_code == 404
    assert api.post("/resource-allocations", mgr, {"resource_id": r["id"], "project_id": 9999, "quantity": 1}).status_code == 404
    planning = api.project(mgr, "Still Planning")
    assert api.post("/resource-allocations", mgr, {"resource_id": r["id"], "project_id": planning["id"], "quantity": 1}).status_code == 422
    assert api.get(f"/resources/{r['id']}", mgr, 200).json()["quantity"] == 10


def test_permissions(api, auth, admin):
    mgr = auth(Role.NGO_MANAGER)
    p = api.approved_project(mgr, admin)
    r = api.resource(mgr, "Tents", 10, 1)
    body = {"resource_id": r["id"], "project_id": p["id"], "quantity": 1}
    for role in (Role.VOLUNTEER, Role.DONOR, Role.FINANCE_OFFICER, Role.VOLUNTEER_COORDINATOR):
        assert api.post("/resource-allocations", auth(role), body).status_code == 403, role
