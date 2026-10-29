from app.utils.enums import Role
from tests.helpers import d


def setup(api, auth, admin):
    mgr = auth(Role.NGO_MANAGER)
    p = api.approved_project(mgr, admin)
    m = api.post("/milestones", mgr, {"project_id": p["id"], "title": "Build", "due_date": d(40)}, 201).json()
    return mgr, p, m


def task(api, h, m, title="Lay bricks", deadline=10, **kw):
    return api.post("/tasks", h, {"milestone_id": m["id"], "title": title, "deadline": d(deadline), **kw}, 201).json()


def test_create_assign_prioritise(api, auth, admin):
    mgr, p, m = setup(api, auth, admin)
    h, vol = api.volunteer_login("worker@example.org")
    me = api.get("/auth/me", h, 200).json()
    t = task(api, mgr, m, priority="critical", assignee_id=me["id"], description="Urgent")
    assert t["priority"] == "critical" and t["assignee_id"] == me["id"] and t["status"] == "todo" and t["progress"] == 0 and not t["is_overdue"]
    assert api.post("/tasks", mgr, {"milestone_id": m["id"], "title": "Ghost", "deadline": d(5), "assignee_id": 9999}).status_code == 404
    assert api.post("/tasks", mgr, {"milestone_id": 9999, "title": "Orphan", "deadline": d(5)}).status_code == 404
    assert api.post("/tasks", mgr, {"milestone_id": m["id"], "title": "Way late", "deadline": d(900)}).status_code == 422
    assert api.post("/tasks", mgr, {"milestone_id": m["id"], "title": "Bad prio", "deadline": d(5), "priority": "urgent!!"}).status_code == 422


def test_status_and_progress_stay_consistent(api, auth, admin):
    mgr, _, m = setup(api, auth, admin)
    t = task(api, mgr, m)
    tid = t["id"]
    r = api.patch(f"/tasks/{tid}", mgr, {"progress": 40}, 200).json()
    assert (r["status"], r["progress"]) == ("in_progress", 40)
    r = api.patch(f"/tasks/{tid}", mgr, {"status": "completed"}, 200).json()
    assert (r["status"], r["progress"]) == ("completed", 100)
    r = api.patch(f"/tasks/{tid}", mgr, {"status": "in_progress"}, 200).json()
    assert r["progress"] == 90  # re-opening a finished task cannot leave it at 100%
    r = api.patch(f"/tasks/{tid}", mgr, {"status": "todo"}, 200).json()
    assert (r["status"], r["progress"]) == ("todo", 0)
    assert api.patch(f"/tasks/{tid}", mgr, {"status": "completed", "progress": 50}).status_code == 422
    assert api.patch(f"/tasks/{tid}", mgr, {"progress": 101}).status_code == 422
    assert api.patch(f"/tasks/{tid}", mgr, {"progress": -1}).status_code == 422
    assert api.patch(f"/tasks/{tid}", mgr, {"status": "blocked"}, 200).json()["status"] == "blocked"


def test_overdue_tasks_are_flagged(api, auth, admin):
    mgr, p, m = setup(api, auth, admin)
    late = task(api, mgr, m, "Late one", deadline=-3)
    task(api, mgr, m, "Future one", deadline=10)
    done = task(api, mgr, m, "Late but done", deadline=-2)
    api.patch(f"/tasks/{done['id']}", mgr, {"status": "completed"}, 200)
    assert api.get(f"/tasks/{late['id']}", mgr, 200).json()["is_overdue"] is True
    over = api.get("/tasks/overdue", mgr, 200).json()
    assert [t["title"] for t in over["items"]] == ["Late one"]
    assert api.get("/tasks", mgr, 200, overdue_only=True, project_id=p["id"]).json()["total"] == 1


def test_filtering(api, auth, admin):
    mgr, p, m = setup(api, auth, admin)
    task(api, mgr, m, "Low", priority="low", deadline=5)
    t = task(api, mgr, m, "High", priority="high", deadline=3)
    api.patch(f"/tasks/{t['id']}", mgr, {"progress": 10}, 200)
    assert api.get("/tasks", mgr, 200, priority="high").json()["total"] == 1
    assert api.get("/tasks", mgr, 200, status="in_progress").json()["items"][0]["title"] == "High"
    assert api.get("/tasks", mgr, 200, milestone_id=m["id"], sort_by="deadline").json()["items"][0]["title"] == "High"
    assert api.get("/tasks", mgr, 200, project_id=p["id"]).json()["total"] == 2


def test_assignee_updates_only_status_and_progress_of_own_tasks(api, auth, admin):
    mgr, _, m = setup(api, auth, admin)
    h, _vol = api.volunteer_login("doer@example.org")
    me = api.get("/auth/me", h, 200).json()
    mine, theirs = task(api, mgr, m, "Mine", assignee_id=me["id"]), task(api, mgr, m, "Not mine")
    r = api.patch(f"/tasks/{mine['id']}", h, {"progress": 60}, 200).json()
    assert r["progress"] == 60 and r["status"] == "in_progress"
    assert api.patch(f"/tasks/{mine['id']}", h, {"title": "Renamed"}).status_code == 403
    assert api.patch(f"/tasks/{mine['id']}", h, {"priority": "low"}).status_code == 403
    assert api.patch(f"/tasks/{mine['id']}", h, {"assignee_id": me["id"]}).status_code == 403
    assert api.patch(f"/tasks/{theirs['id']}", h, {"progress": 100}).status_code == 403
    assert api.get("/tasks", h, 200).json()["total"] == 1  # volunteers only list their own
    assert api.get("/tasks", h, assignee_id=1234).status_code == 403
    assert api.post("/tasks", h, {"milestone_id": m["id"], "title": "Self-assigned", "deadline": d(4)}).status_code == 403
    assert api.c.delete(f"/api/v1/tasks/{mine['id']}", headers=h).status_code == 403


def test_deleting_a_task_updates_milestone(api, auth, admin):
    mgr, _, m = setup(api, auth, admin)
    a, b = task(api, mgr, m, "Task A"), task(api, mgr, m, "Task B")
    api.patch(f"/tasks/{a['id']}", mgr, {"status": "completed"}, 200)
    assert api.get(f"/milestones/{m['id']}", mgr, 200).json()["status"] == "in_progress"
    assert api.c.delete(f"/api/v1/tasks/{b['id']}", headers=mgr).status_code == 200
    assert api.get(f"/milestones/{m['id']}", mgr, 200).json()["status"] == "completed"
    assert api.get(f"/tasks/{b['id']}", mgr).status_code == 404


def test_closed_project_blocks_task_changes(api, auth, admin):
    mgr, p, m = setup(api, auth, admin)
    t = task(api, mgr, m)
    api.patch(f"/milestones/{m['id']}", mgr, {}, 200)
    api.post(f"/projects/{p['id']}/status", admin, {"status": "cancelled"}, 200)
    assert api.patch(f"/tasks/{t['id']}", mgr, {"progress": 50}).status_code == 422
    assert api.post("/tasks", mgr, {"milestone_id": m["id"], "title": "Nope nope", "deadline": d(5)}).status_code == 422
