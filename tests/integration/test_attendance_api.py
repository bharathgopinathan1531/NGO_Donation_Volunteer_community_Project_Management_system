from app.utils.enums import Role
from tests.helpers import d


def make_assignment(api, auth, admin, volunteer=None, start=-10, end=10):
    coord = auth(Role.VOLUNTEER_COORDINATOR)
    vol = volunteer or api.volunteer(coord)
    project = api.approved_project(auth(Role.NGO_MANAGER), admin)
    a = api.post("/assignments", coord, {"volunteer_id": vol["id"], "project_id": project["id"], "responsibility": "Helper", "start_date": d(start), "end_date": d(end)}, 201).json()
    return coord, a


def test_record_attendance_accumulates_hours(api, auth, admin):
    coord, a = make_assignment(api, auth, admin)
    r = api.post("/attendance", coord, {"assignment_id": a["id"], "attendance_date": d(-3), "hours": "4.25", "notes": "Painting"}, 201).json()
    assert r["status"] == "present" and r["hours"] == "4.25" and r["recorded_by"]
    api.post("/attendance", coord, {"assignment_id": a["id"], "attendance_date": d(-2), "hours": "2"}, 201)
    got = api.get(f"/assignments/{a['id']}", coord, 200).json()
    assert got["hours_completed"] == "6.25" and got["status"] == "active"  # first attendance activates the assignment


def test_absences_carry_no_hours(api, auth, admin):
    coord, a = make_assignment(api, auth, admin)
    api.post("/attendance", coord, {"assignment_id": a["id"], "attendance_date": d(-3), "status": "absent"}, 201)
    assert api.post("/attendance", coord, {"assignment_id": a["id"], "attendance_date": d(-2), "status": "absent", "hours": "3"}).status_code == 422
    assert api.post("/attendance", coord, {"assignment_id": a["id"], "attendance_date": d(-1), "status": "present", "hours": "0"}).status_code == 422
    assert api.get(f"/assignments/{a['id']}", coord, 200).json()["hours_completed"] == "0.00"


def test_one_record_per_assignment_per_day(api, auth, admin):
    coord, a = make_assignment(api, auth, admin)
    body = {"assignment_id": a["id"], "attendance_date": d(-1), "hours": "3"}
    api.post("/attendance", coord, body, 201)
    assert api.post("/attendance", coord, body).status_code == 409


def test_date_rules(api, auth, admin):
    coord, a = make_assignment(api, auth, admin, start=-5, end=5)
    assert api.post("/attendance", coord, {"assignment_id": a["id"], "attendance_date": d(-20), "hours": "1"}).status_code == 422  # before start
    assert api.post("/attendance", coord, {"assignment_id": a["id"], "attendance_date": d(3), "hours": "1"}).status_code == 422  # future
    assert api.post("/attendance", coord, {"assignment_id": 999, "attendance_date": d(-1), "hours": "1"}).status_code == 404
    assert api.post("/attendance", coord, {"assignment_id": a["id"], "attendance_date": d(-1), "hours": "25"}).status_code == 422


def test_correcting_a_record_recomputes_total(api, auth, admin):
    coord, a = make_assignment(api, auth, admin)
    r = api.post("/attendance", coord, {"assignment_id": a["id"], "attendance_date": d(-1), "hours": "8"}, 201).json()
    api.patch(f"/attendance/{r['id']}", coord, {"hours": "5"}, 200)
    assert api.get(f"/assignments/{a['id']}", coord, 200).json()["hours_completed"] == "5.00"
    api.patch(f"/attendance/{r['id']}", coord, {"status": "excused"}, 200)  # hours zeroed automatically
    assert api.get(f"/assignments/{a['id']}", coord, 200).json()["hours_completed"] == "0.00"
    assert api.patch(f"/attendance/{r['id']}", coord, {"status": "present"}).status_code == 422  # present needs hours


def test_no_attendance_on_cancelled_assignment(api, auth, admin):
    coord, a = make_assignment(api, auth, admin)
    api.post(f"/assignments/{a['id']}/status", coord, {"status": "cancelled"}, 200)
    assert api.post("/attendance", coord, {"assignment_id": a["id"], "attendance_date": d(-1), "hours": "1"}).status_code == 422


def test_volunteers_cannot_self_report_but_can_view_their_own(api, auth, admin):
    h, profile = api.volunteer_login("att@example.org")
    coord, a = make_assignment(api, auth, admin, volunteer=profile)
    assert api.post("/attendance", h, {"assignment_id": a["id"], "attendance_date": d(-1), "hours": "9"}).status_code == 403
    api.post("/attendance", coord, {"assignment_id": a["id"], "attendance_date": d(-1), "hours": "3"}, 201)
    other_h, _ = api.volunteer_login("nosy@example.org")
    assert api.get("/attendance", h, 200).json()["total"] == 1
    assert api.get("/attendance", other_h, 200).json()["total"] == 0
    assert api.get("/attendance", other_h, assignment_id=a["id"]).status_code == 404
    assert api.get("/attendance", coord, 200, date_from=d(-1), date_to=d(0), status="present").json()["total"] == 1
