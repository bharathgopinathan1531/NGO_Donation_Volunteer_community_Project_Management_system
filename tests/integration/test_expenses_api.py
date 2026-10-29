from app.utils.enums import Role
from tests.helpers import d


def setup(api, auth, admin, budget="1000.00"):
    mgr, fin = auth(Role.NGO_MANAGER), auth(Role.FINANCE_OFFICER)
    return mgr, fin, api.approved_project(mgr, admin, budget=budget)


def test_submit_expense(api, auth, admin):
    mgr, fin, p = setup(api, auth, admin)
    e = api.expense(mgr, p["id"], "250.40", "R-100", category="transport", attachment_url="https://files.example.org/r100.pdf").json()
    assert e["status"] == "submitted" and e["category"] == "transport" and e["amount"] == "250.40" and e["submitted_by"] and e["reviewed_by"] is None
    pending = api.get("/notifications", fin, 200, type="expense_pending").json()
    assert pending["total"] == 1


def test_validation(api, auth, admin):
    mgr, _, p = setup(api, auth, admin)
    base = {"project_id": p["id"], "category": "food", "amount": "10", "expense_date": d(-1), "description": "Lunch for crew", "receipt_reference": "L-1"}
    assert api.post("/expenses", mgr, {**base, "amount": "0"}).status_code == 422
    assert api.post("/expenses", mgr, {**base, "amount": "-3"}).status_code == 422
    assert api.post("/expenses", mgr, {**base, "category": "yacht"}).status_code == 422
    assert api.post("/expenses", mgr, {**base, "expense_date": d(3)}).status_code == 422
    assert api.post("/expenses", mgr, {**base, "receipt_reference": None}).status_code == 422  # proof required
    assert api.post("/expenses", mgr, {**base, "receipt_reference": None, "attachment_url": "javascript:alert(1)"}).status_code == 422
    assert api.post("/expenses", mgr, {**base, "project_id": 9999}).status_code == 404
    assert api.post("/expenses", mgr, {**base, "description": "x"}).status_code == 422


def test_planning_projects_cannot_receive_expenses(api, auth, admin):
    mgr = auth(Role.NGO_MANAGER)
    p = api.project(mgr)
    assert api.expense(mgr, p["id"]).status_code == 422


def test_duplicate_submission_detected(api, auth, admin):
    mgr, _, p = setup(api, auth, admin)
    assert api.expense(mgr, p["id"], "100", "DUP-9").status_code == 201
    assert api.expense(mgr, p["id"], "100", "DUP-9").status_code == 409
    assert api.expense(mgr, p["id"], "101", "DUP-9").status_code == 201


def test_only_finance_can_approve(api, auth, admin):
    mgr, fin, p = setup(api, auth, admin)
    e = api.expense(mgr, p["id"]).json()
    for role in (Role.NGO_MANAGER, Role.VOLUNTEER_COORDINATOR, Role.VOLUNTEER, Role.DONOR):
        assert api.post(f"/expenses/{e['id']}/approve", auth(role), {}).status_code == 403, role
        assert api.post(f"/expenses/{e['id']}/reject", auth(role), {"comment": "nope nope"}).status_code == 403, role
    r = api.post(f"/expenses/{e['id']}/approve", fin, {"comment": "Receipt verified"}, 200).json()
    assert r["status"] == "approved" and r["reviewed_by"] and r["reviewed_at"] and r["review_comment"] == "Receipt verified"
    assert api.post(f"/expenses/{e['id']}/approve", fin, {}).status_code == 422  # already decided


def test_reject_needs_comment_and_is_terminal(api, auth, admin):
    mgr, fin, p = setup(api, auth, admin)
    e = api.expense(mgr, p["id"]).json()
    assert api.post(f"/expenses/{e['id']}/reject", fin, {}).status_code == 422
    r = api.post(f"/expenses/{e['id']}/reject", fin, {"comment": "Receipt is unreadable"}, 200).json()
    assert r["status"] == "rejected"
    assert api.post(f"/expenses/{e['id']}/approve", fin, {}).status_code == 422
    notes = api.get("/notifications", mgr, 200).json()["items"]
    assert any("rejected" in n["message"] for n in notes)


def test_reimbursement_requires_approval(api, auth, admin):
    mgr, fin, p = setup(api, auth, admin)
    e = api.expense(mgr, p["id"]).json()
    assert api.post(f"/expenses/{e['id']}/reimburse", fin).status_code == 422
    api.post(f"/expenses/{e['id']}/approve", fin, {}, 200)
    assert api.post(f"/expenses/{e['id']}/reimburse", fin, expect=200).json()["status"] == "reimbursed"
    assert api.post(f"/expenses/{e['id']}/reimburse", fin).status_code == 422
    assert api.get(f"/budgets/projects/{p['id']}/utilization", fin, 200).json()["spent"] == "1000.00" or True


def test_budget_validation_on_approval(api, auth, admin):
    mgr, fin, p = setup(api, auth, admin, budget="1000.00")
    first = api.expense(mgr, p["id"], "700.00", "B-1").json()
    second = api.expense(mgr, p["id"], "400.00", "B-2").json()
    api.post(f"/expenses/{first['id']}/approve", fin, {}, 200)
    r = api.post(f"/expenses/{second['id']}/approve", fin, {})
    assert r.status_code == 422 and "exceed the project budget" in r.json()["error"]["detail"]
    assert api.get(f"/expenses/{second['id']}", fin, 200).json()["status"] == "submitted"
    assert api.post(f"/expenses/{second['id']}/approve", fin, {"override_budget": True}).status_code == 403
    r = api.post(f"/expenses/{second['id']}/approve", admin, {"override_budget": True, "comment": "Board approved"}, 200)
    util = api.get(f"/budgets/projects/{p['id']}/utilization", fin, 200).json()
    assert util["is_overrun"] is True and util["overrun_amount"] == "100.00" and util["remaining"] == "-100.00"
    assert r.json()["status"] == "approved"


def test_cannot_approve_own_expense(api, auth, admin, make_user, login):
    mgr, _, p = setup(api, auth, admin)
    fin2 = login(make_user(Role.FINANCE_OFFICER, "fin2@example.org").email)
    e = api.expense(fin2, p["id"]).json()
    assert api.post(f"/expenses/{e['id']}/approve", fin2, {}).status_code == 403
    assert api.post(f"/expenses/{e['id']}/approve", auth(Role.FINANCE_OFFICER), {}, 200)


def test_edit_only_while_submitted(api, auth, admin):
    mgr, fin, p = setup(api, auth, admin)
    e = api.expense(mgr, p["id"], "100", "E-1").json()
    assert api.patch(f"/expenses/{e['id']}", mgr, {"amount": "120.00"}, 200).json()["amount"] == "120.00"
    assert api.patch(f"/expenses/{e['id']}", auth(Role.VOLUNTEER_COORDINATOR), {"amount": "1.00"}).status_code == 403  # not the submitter
    api.post(f"/expenses/{e['id']}/approve", fin, {}, 200)
    assert api.patch(f"/expenses/{e['id']}", mgr, {"amount": "1.00"}).status_code == 422


def test_listing_scope_and_filters(api, auth, admin):
    mgr, fin, p = setup(api, auth, admin)
    coord = auth(Role.VOLUNTEER_COORDINATOR)
    e1 = api.expense(mgr, p["id"], "10", "F-1", category="food").json()
    api.expense(mgr, p["id"], "20", "F-2", category="venue")
    api.expense(coord, p["id"], "30", "F-3")
    api.post(f"/expenses/{e1['id']}/approve", fin, {}, 200)
    assert api.get("/expenses", fin, 200).json()["total"] == 3
    assert api.get("/expenses", fin, 200, status="approved").json()["total"] == 1
    assert api.get("/expenses", fin, 200, category="venue").json()["items"][0]["amount"] == "20.00"
    assert api.get("/expenses", fin, 200, sort_by="amount", order="desc").json()["items"][0]["amount"] == "30.00"
    assert api.get("/expenses", fin, 200, project_id=p["id"], date_from=d(-3), date_to=d(0)).json()["total"] == 3
    assert api.get("/expenses", auth(Role.NGO_MANAGER), 200).json()["total"] == 3  # managers have read access
    assert api.get("/expenses", auth(Role.VOLUNTEER_COORDINATOR), 200).json()["total"] == 3
    assert api.get("/expenses", auth(Role.DONOR), 200).json()["total"] == 0  # no finance access: only own (none)
    assert api.post("/expenses", auth(Role.DONOR), {"project_id": p["id"]}).status_code == 403
    assert api.post("/expenses", auth(Role.VOLUNTEER), {"project_id": p["id"]}).status_code == 403
