from app.utils.enums import Role
from tests.helpers import d

BODY = {"full_name": "Lakshmi Devi", "category": "woman", "age": 34, "phone": "+919876543210", "address": "12 Lake Road", "national_id": "XX-1234", "notes": "Needs rations"}


def test_register_map_and_update(api, auth, admin):
    mgr = auth(Role.NGO_MANAGER)
    p = api.approved_project(mgr, admin)
    b = api.post("/beneficiaries", mgr, {**BODY, "project_ids": [p["id"]]}, 201).json()
    assert b["project_ids"] == [p["id"]] and b["phone"] == "+919876543210"
    p2 = api.approved_project(mgr, admin, name="Second Project")
    assert api.post(f"/beneficiaries/{b['id']}/projects/{p2['id']}", mgr, expect=200).json()["project_ids"] == sorted([p["id"], p2["id"]])
    assert api.c.delete(f"/api/v1/beneficiaries/{b['id']}/projects/{p['id']}", headers=mgr).json()["project_ids"] == [p2["id"]]
    assert api.patch(f"/beneficiaries/{b['id']}", mgr, {"age": 35}, 200).json()["age"] == 35
    assert api.post("/beneficiaries", mgr, {**BODY, "project_ids": [9999]}).status_code == 404
    assert api.post("/beneficiaries", mgr, {**BODY, "age": 200}).status_code == 422
    assert api.post("/beneficiaries", mgr, {**BODY, "category": "aliens"}).status_code == 422


def test_sensitive_fields_are_redacted_for_unprivileged_roles(api, auth):
    mgr, coord = auth(Role.NGO_MANAGER), auth(Role.VOLUNTEER_COORDINATOR)
    b = api.post("/beneficiaries", mgr, BODY, 201).json()
    seen = api.get(f"/beneficiaries/{b['id']}", coord, 200).json()
    assert seen["full_name"] == "Lakshmi Devi"
    for f in ("phone", "address", "national_id", "notes"):
        assert seen[f] is None, f
    row = api.get("/beneficiaries", coord, 200).json()["items"][0]
    assert row["national_id"] is None
    assert api.get(f"/beneficiaries/{b['id']}", mgr, 200).json()["national_id"] == "XX-1234"


def test_sensitive_data_never_reaches_audit_log(api, auth, admin):
    mgr = auth(Role.NGO_MANAGER)
    api.post("/beneficiaries", mgr, BODY, 201)
    logs = api.get("/audit-logs", admin, 200, entity="beneficiary").json()
    assert logs["total"] >= 1 and "XX-1234" not in str(logs) and "12 Lake Road" not in str(logs)


def test_filters_and_permissions(api, auth):
    mgr = auth(Role.NGO_MANAGER)
    api.post("/beneficiaries", mgr, BODY, 201)
    api.post("/beneficiaries", mgr, {**BODY, "full_name": "Child One", "category": "child", "national_id": None}, 201)
    assert api.get("/beneficiaries", mgr, 200, category="child").json()["total"] == 1
    assert api.get("/beneficiaries", mgr, 200, search="lakshmi").json()["total"] == 1
    for role in (Role.VOLUNTEER, Role.DONOR, Role.FINANCE_OFFICER):
        assert api.get("/beneficiaries", auth(role)).status_code == 403, role
    assert api.post("/beneficiaries", auth(Role.FINANCE_OFFICER), BODY).status_code == 403
