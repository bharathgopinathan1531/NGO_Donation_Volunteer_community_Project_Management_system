from app.utils.enums import Role


def test_register_and_update(api, auth):
    mgr = auth(Role.NGO_MANAGER)
    r = api.resource(mgr, "Blankets", 50, 5)
    assert r["quantity"] == 50 and r["is_low_stock"] is False
    assert api.patch(f"/resources/{r['id']}", mgr, {"low_stock_threshold": 60}, 200).json()["is_low_stock"] is True
    assert api.patch(f"/resources/{r['id']}", mgr, {"quantity": 1}, 200).json()["quantity"] == 50  # stock only moves via ledger
    assert api.post("/resources", mgr, {"name": "Bad", "category": "nonsense"}).status_code == 422
    assert api.post("/resources", mgr, {"name": "Neg", "category": "food_package", "initial_quantity": -1}).status_code == 422
    assert api.get("/resources/9999", mgr).status_code == 404


def test_stock_in_out_and_ledger(api, auth):
    mgr = auth(Role.NGO_MANAGER)
    r = api.resource(mgr, "Rice Bags", 20, 5)
    rid = r["id"]
    t = api.post(f"/resources/{rid}/stock-in", mgr, {"quantity": 30, "reference": "PO-1"}, 201).json()
    assert t["transaction_type"] == "stock_in" and t["balance_after"] == 50
    t = api.post(f"/resources/{rid}/stock-out", mgr, {"quantity": 15, "reason": "Village drive"}, 201).json()
    assert t["transaction_type"] == "stock_out" and t["balance_after"] == 35
    assert api.get(f"/resources/{rid}", mgr, 200).json()["quantity"] == 35
    ledger = api.get("/resources/transactions", mgr, 200, resource_id=rid).json()
    assert ledger["total"] == 3 and [x["balance_after"] for x in ledger["items"]].count(35) == 1


def test_no_negative_stock_and_validation(api, auth):
    mgr = auth(Role.NGO_MANAGER)
    r = api.resource(mgr, "Kits", 5, 1)
    assert api.post(f"/resources/{r['id']}/stock-out", mgr, {"quantity": 6, "reason": "Too many"}).status_code == 422
    assert api.post(f"/resources/{r['id']}/stock-out", mgr, {"quantity": 1}).status_code == 422  # reason mandatory
    assert api.post(f"/resources/{r['id']}/stock-in", mgr, {"quantity": 0}).status_code == 422
    assert api.get(f"/resources/{r['id']}", mgr, 200).json()["quantity"] == 5


def test_low_stock_alert_and_notification(api, auth):
    mgr = auth(Role.NGO_MANAGER)
    r = api.resource(mgr, "Medicine", 12, 10)
    assert api.get("/resources/low-stock", mgr, 200).json() == []
    api.post(f"/resources/{r['id']}/stock-out", mgr, {"quantity": 5, "reason": "Camp"}, 201)
    assert [x["name"] for x in api.get("/resources/low-stock", mgr, 200).json()] == ["Medicine"]
    assert api.get("/notifications", mgr, 200, type="low_stock").json()["total"] >= 1


def test_filters_and_permissions(api, auth):
    mgr = auth(Role.NGO_MANAGER)
    api.resource(mgr, "Apples", 5)
    api.resource(mgr, "Books", 5, category="educational_material")
    assert api.get("/resources", mgr, 200, search="app").json()["total"] == 1
    assert api.get("/resources", mgr, 200, category="educational_material").json()["total"] == 1
    for role in (Role.VOLUNTEER, Role.DONOR):
        assert api.get("/resources", auth(role)).status_code == 403
    assert api.get("/resources", auth(Role.FINANCE_OFFICER)).status_code == 200
    assert api.post("/resources", auth(Role.FINANCE_OFFICER), {"name": "Nope", "category": "food_package"}).status_code == 403
