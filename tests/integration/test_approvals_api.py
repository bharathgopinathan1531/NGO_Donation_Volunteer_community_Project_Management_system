from app.utils.enums import Role


def test_submit_approve_flow_records_history(api, auth, admin):
    mgr = auth(Role.NGO_MANAGER)
    p = api.project(mgr)
    sub = api.post(f"/projects/{p['id']}/submit", mgr, {"comments": "Ready for review"}, 201).json()
    assert sub["action"] == "submitted" and sub["comments"] == "Ready for review" and sub["actor_id"]
    assert api.get(f"/projects/{p['id']}", admin, 200).json()["approval_state"] == "submitted"
    dec = api.post(f"/projects/{p['id']}/approve", admin, {"comments": "Approved with thanks"}, 200).json()
    assert dec["action"] == "approved"
    got = api.get(f"/projects/{p['id']}", admin, 200).json()
    assert got["status"] == "approved" and got["approval_state"] == "approved"
    hist = api.get(f"/projects/{p['id']}/approvals", admin, 200).json()
    assert [(h["action"], h["comments"]) for h in hist] == [("submitted", "Ready for review"), ("approved", "Approved with thanks")]


def test_rejection_requires_a_reason_and_allows_resubmission(api, auth, admin):
    mgr = auth(Role.NGO_MANAGER)
    p = api.project(mgr)
    api.post(f"/projects/{p['id']}/submit", mgr, {}, 201)
    assert api.post(f"/projects/{p['id']}/reject", admin, {}).status_code == 422
    assert api.post(f"/projects/{p['id']}/reject", admin, {"comments": "ok"}).status_code == 422  # too short
    api.post(f"/projects/{p['id']}/reject", admin, {"comments": "Budget breakdown missing"}, 200)
    got = api.get(f"/projects/{p['id']}", admin, 200).json()
    assert got["status"] == "planning" and got["approval_state"] == "rejected"
    api.post(f"/projects/{p['id']}/submit", mgr, {"comments": "Added budget"}, 201)
    api.post(f"/projects/{p['id']}/approve", admin, {}, 200)
    assert [h["action"] for h in api.get(f"/projects/{p['id']}/approvals", admin, 200).json()] == ["submitted", "rejected", "submitted", "approved"]


def test_workflow_state_guards(api, auth, admin):
    mgr = auth(Role.NGO_MANAGER)
    p = api.project(mgr)
    assert api.post(f"/projects/{p['id']}/approve", admin, {}).status_code == 422  # never submitted
    api.post(f"/projects/{p['id']}/submit", mgr, {}, 201)
    assert api.post(f"/projects/{p['id']}/submit", mgr, {}).status_code == 409  # already pending
    api.post(f"/projects/{p['id']}/approve", admin, {}, 200)
    assert api.post(f"/projects/{p['id']}/approve", admin, {}).status_code == 422  # already decided
    assert api.post(f"/projects/{p['id']}/submit", mgr, {}).status_code == 422  # no longer in planning
    assert api.post("/projects/9999/submit", mgr, {}).status_code == 404


def test_role_restrictions(api, auth, admin):
    mgr = auth(Role.NGO_MANAGER)
    p = api.project(mgr)
    assert api.post(f"/projects/{p['id']}/submit", auth(Role.FINANCE_OFFICER), {}).status_code == 403
    assert api.post(f"/projects/{p['id']}/submit", auth(Role.VOLUNTEER), {}).status_code == 403
    assert api.post(f"/projects/{p['id']}/submit", auth(Role.VOLUNTEER_COORDINATOR), {}, 201)  # coordinators may submit
    for role in (Role.VOLUNTEER_COORDINATOR, Role.FINANCE_OFFICER, Role.VOLUNTEER, Role.DONOR):
        assert api.post(f"/projects/{p['id']}/approve", auth(role), {}).status_code == 403, role
    assert api.get("/approvals/pending", auth(Role.FINANCE_OFFICER)).status_code == 403


def test_manager_cannot_approve_own_submission_but_a_peer_can(api, auth, admin, make_user, login):
    mgr = auth(Role.NGO_MANAGER)
    p = api.project(mgr)
    api.post(f"/projects/{p['id']}/submit", mgr, {}, 201)
    assert api.post(f"/projects/{p['id']}/approve", mgr, {}).status_code == 403
    peer = login(make_user(Role.NGO_MANAGER, "peer@example.org").email)
    assert api.post(f"/projects/{p['id']}/approve", peer, {}, 200)


def test_pending_queue(api, auth, admin):
    mgr = auth(Role.NGO_MANAGER)
    a, b = api.project(mgr, "Project A"), api.project(mgr, "Project B")
    api.post(f"/projects/{a['id']}/submit", mgr, {}, 201)
    api.post(f"/projects/{b['id']}/submit", mgr, {}, 201)
    api.post(f"/projects/{b['id']}/approve", admin, {}, 200)
    pending = api.get("/approvals/pending", admin, 200).json()
    assert pending["total"] == 1 and pending["items"][0]["project_id"] == a["id"]


def test_decision_notifications(api, auth, admin):
    mgr = auth(Role.NGO_MANAGER)
    p = api.project(mgr)
    api.post(f"/projects/{p['id']}/submit", mgr, {}, 201)
    req = api.get("/notifications", admin, 200).json()
    assert [n["type"] for n in req["items"]] == ["project_approval_request"]
    api.post(f"/projects/{p['id']}/approve", admin, {"comments": "Go ahead"}, 200)
    got = api.get("/notifications", mgr, 200, type="project_approval_decision").json()
    assert got["total"] == 1 and "approved" in got["items"][0]["message"] and "Go ahead" in got["items"][0]["message"]
