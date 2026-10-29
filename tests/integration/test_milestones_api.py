from app.utils.enums import Role
from tests.helpers import d


def ms(api, h, project, title="Foundation", due=30, **kw):
    return api.post("/milestones", h, {"project_id": project["id"], "title": title, "due_date": d(due), **kw}, 201).json()


def test_create_and_track(api, auth, admin):
    mgr = auth(Role.NGO_MANAGER)
    p = api.approved_project(mgr, admin)
    m = ms(api, mgr, p)
    assert m["status"] == "pending" and m["progress_pct"] == 0.0 and m["is_overdue"] is False and m["tasks_total"] == 0
    listing = api.get(f"/projects/{p['id']}/milestones", mgr, 200).json()
    assert [x["id"] for x in listing] == [m["id"]]


def test_due_date_must_be_inside_project_period(api, auth, admin):
    mgr = auth(Role.NGO_MANAGER)
    p = api.approved_project(mgr, admin)
    for due in (-500, 500):
        assert api.post("/milestones", mgr, {"project_id": p["id"], "title": "Bad due date", "due_date": d(due)}).status_code == 422
    assert api.post("/milestones", mgr, {"project_id": 9999, "title": "Orphan", "due_date": d(1)}).status_code == 404


def test_status_follows_task_progress(api, auth, admin):
    mgr = auth(Role.NGO_MANAGER)
    p = api.approved_project(mgr, admin)
    m = ms(api, mgr, p)
    t1 = api.post("/tasks", mgr, {"milestone_id": m["id"], "title": "Task one", "deadline": d(10)}, 201).json()
    t2 = api.post("/tasks", mgr, {"milestone_id": m["id"], "title": "Task two", "deadline": d(12)}, 201).json()
    assert api.get(f"/milestones/{m['id']}", mgr, 200).json()["status"] == "pending"
    api.patch(f"/tasks/{t1['id']}", mgr, {"progress": 50}, 200)
    got = api.get(f"/milestones/{m['id']}", mgr, 200).json()
    assert got["status"] == "in_progress" and got["progress_pct"] == 25.0 and got["tasks_total"] == 2
    api.patch(f"/tasks/{t1['id']}", mgr, {"status": "completed"}, 200)
    api.patch(f"/tasks/{t2['id']}", mgr, {"progress": 100}, 200)
    done = api.get(f"/milestones/{m['id']}", mgr, 200).json()
    assert done["status"] == "completed" and done["completed_at"] and done["progress_pct"] == 100.0 and done["tasks_completed"] == 2
    api.post("/tasks", mgr, {"milestone_id": m["id"], "title": "Late addition", "deadline": d(14)}, 201)
    assert api.get(f"/milestones/{m['id']}", mgr, 200).json()["status"] == "in_progress"  # reopened by the new task


def test_manual_status_only_without_tasks(api, auth, admin):
    mgr = auth(Role.NGO_MANAGER)
    p = api.approved_project(mgr, admin)
    empty, busy = ms(api, mgr, p, "Empty"), ms(api, mgr, p, "Busy")
    api.post("/tasks", mgr, {"milestone_id": busy["id"], "title": "Some task", "deadline": d(5)}, 201)
    assert api.patch(f"/milestones/{busy['id']}", mgr, {"status": "completed"}).status_code == 422
    r = api.patch(f"/milestones/{empty['id']}", mgr, {"status": "completed"}, 200).json()
    assert r["status"] == "completed" and r["progress_pct"] == 100.0


def test_overdue_identification(api, auth, admin):
    mgr = auth(Role.NGO_MANAGER)
    p = api.approved_project(mgr, admin)
    late, fine = ms(api, mgr, p, "Late", due=-5), ms(api, mgr, p, "Future", due=20)
    done = ms(api, mgr, p, "Old but done", due=-3)
    api.patch(f"/milestones/{done['id']}", mgr, {"status": "completed"}, 200)
    overdue = api.get("/milestones", mgr, 200, overdue_only=True).json()
    assert [m["title"] for m in overdue["items"]] == ["Late"] and overdue["items"][0]["is_overdue"] is True
    assert api.get(f"/milestones/{fine['id']}", mgr, 200).json()["is_overdue"] is False
    assert late


def test_delete_rules(api, auth, admin):
    mgr = auth(Role.NGO_MANAGER)
    p = api.approved_project(mgr, admin)
    empty, busy = ms(api, mgr, p, "Empty"), ms(api, mgr, p, "Busy")
    api.post("/tasks", mgr, {"milestone_id": busy["id"], "title": "A task", "deadline": d(5)}, 201)
    assert api.c.delete(f"/api/v1/milestones/{busy['id']}", headers=mgr).status_code == 422
    assert api.c.delete(f"/api/v1/milestones/{empty['id']}", headers=mgr).status_code == 200
    assert api.get(f"/milestones/{empty['id']}", mgr).status_code == 404


def test_closed_projects_are_frozen(api, auth, admin):
    mgr = auth(Role.NGO_MANAGER)
    p = api.approved_project(mgr, admin)
    api.post(f"/projects/{p['id']}/status", admin, {"status": "cancelled"}, 200)
    assert api.post("/milestones", mgr, {"project_id": p["id"], "title": "Too late", "due_date": d(5)}).status_code == 422


def test_permissions(api, auth, admin):
    mgr = auth(Role.NGO_MANAGER)
    p = api.approved_project(mgr, admin)
    body = {"project_id": p["id"], "title": "Forbidden", "due_date": d(5)}
    for role in (Role.FINANCE_OFFICER, Role.VOLUNTEER, Role.DONOR):
        assert api.post("/milestones", auth(role), body).status_code == 403, role
    assert api.post("/milestones", auth(Role.VOLUNTEER_COORDINATOR), body, 201)
    assert api.get("/milestones", auth(Role.VOLUNTEER)).status_code == 403  # must name a project they belong to
