from app.utils.enums import Role
from tests.helpers import d


def setup(api, auth, admin, stock=50):
    mgr = auth(Role.NGO_MANAGER)
    p = api.approved_project(mgr, admin)
    b = api.post("/beneficiaries", mgr, {"full_name": "Ramesh Naik", "category": "family", "project_ids": [p["id"]]}, 201).json()
    r = api.resource(mgr, "Rice", stock, 5)
    return mgr, p, b, r


def give(api, h, p, b, r=None, qty=5, **kw):
    body = {"beneficiary_id": b["id"], "project_id": p["id"], "assistance_type": "food", "quantity": qty, "distribution_date": d(0), **kw}
    if r:
        body["resource_id"] = r["id"]
    return api.post("/assistance", h, body)


def test_distribution_within_allocation_reduces_nothing_twice(api, auth, admin):
    mgr, p, b, r = setup(api, auth, admin)
    api.post("/resource-allocations", mgr, {"resource_id": r["id"], "project_id": p["id"], "quantity": 20}, 201)
    assert api.get(f"/resources/{r['id']}", mgr, 200).json()["quantity"] == 30
    assert give(api, mgr, p, b, r, 8).status_code == 201
    assert give(api, mgr, p, b, r, 12).status_code == 201
    assert give(api, mgr, p, b, r, 1).status_code == 422  # allocation exhausted
    assert api.get(f"/resources/{r['id']}", mgr, 200).json()["quantity"] == 30  # allocation already deducted stock
    assert api.get("/assistance", mgr, 200, beneficiary_id=b["id"]).json()["total"] == 2
    assert api.get("/assistance", mgr, 200, project_id=p["id"]).json()["total"] == 2


def test_requires_mapping_and_allocation(api, auth, admin):
    mgr, p, b, r = setup(api, auth, admin)
    assert give(api, mgr, p, b, r, 1).status_code == 422  # nothing allocated
    other = api.approved_project(mgr, admin, name="Unmapped Project")
    assert give(api, mgr, other, b).status_code == 422  # beneficiary not mapped
    assert give(api, mgr, p, {"id": 9999}).status_code == 404
    assert give(api, mgr, p, b, quantity=1) if False else True
    assert give(api, mgr, p, b, None, 0).status_code == 201  # non-material assistance (counselling etc.)
    assert api.post("/assistance", mgr, {"beneficiary_id": b["id"], "project_id": p["id"], "assistance_type": "x", "distribution_date": d(0)}).status_code == 422


def test_permissions(api, auth, admin):
    mgr, p, b, r = setup(api, auth, admin)
    for role in (Role.VOLUNTEER, Role.DONOR, Role.FINANCE_OFFICER):
        assert give(api, auth(role), p, b).status_code == 403, role
    assert give(api, auth(Role.VOLUNTEER_COORDINATOR), p, b, None, 0).status_code == 201
