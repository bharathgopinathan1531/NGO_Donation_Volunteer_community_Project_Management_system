from app.utils.enums import Role


def seed(api, auth, admin):
    mgr, fin = auth(Role.NGO_MANAGER), auth(Role.FINANCE_OFFICER)
    donor, camp = api.donor(admin), api.campaign(admin)
    api.donation(admin, donor["id"], camp["id"], "300.00", "R-1")
    api.donation(admin, donor["id"], camp["id"], "200.00", "R-2")
    p = api.approved_project(mgr, admin)
    e = api.expense(mgr, p["id"], "120.00", "R-E1").json()
    api.post(f"/expenses/{e['id']}/approve", fin, {}, 200)
    return mgr, fin, p


def test_all_reports_respond(api, auth, admin):
    mgr, fin, _ = seed(api, auth, admin)
    for name in ("donation-summary", "campaign-performance", "expenses", "budget-utilization"):
        r = api.get(f"/reports/{name}", fin, 200).json()
        assert r["columns"] and "rows" in r and r["total"] >= 1, name
    for name in ("volunteer-contribution", "project-progress", "resource-distribution", "beneficiary-impact"):
        assert api.get(f"/reports/{name}", mgr, 200).status_code == 200, name


def test_donation_summary_grouping_and_totals(api, auth, admin):
    _, fin, _ = seed(api, auth, admin)
    for g in ("campaign", "donor", "method", "status", "month"):
        assert api.get("/reports/donation-summary", fin, 200, group_by=g).json()["total"] >= 1, g
    rows = api.get("/reports/donation-summary", fin, 200, group_by="campaign").json()["rows"]
    assert "500" in str(rows[0])
    assert api.get("/reports/donation-summary", fin, group_by="bogus").status_code == 422


def test_csv_export_and_sort_guard(api, auth, admin):
    _, fin, _ = seed(api, auth, admin)
    r = api.c.get("/api/v1/reports/expenses", params={"export": "true"}, headers=fin)
    assert r.status_code == 200 and "text/csv" in r.headers["content-type"] and len(r.text.strip().splitlines()) >= 2
    assert api.get("/reports/expenses", fin, sort_by="password; DROP TABLE users").status_code in (400, 422)


def test_report_permissions(api, auth, admin):
    mgr, fin, _ = seed(api, auth, admin)
    assert api.get("/reports/expenses", auth(Role.VOLUNTEER_COORDINATOR)).status_code == 403
    assert api.get("/reports/project-progress", fin).status_code == 403
    for role in (Role.VOLUNTEER, Role.DONOR):
        assert api.get("/reports/expenses", auth(role)).status_code == 403
        assert api.get("/reports/project-progress", auth(role)).status_code == 403
