"""The mandatory end-to-end demo from the assignment brief, executed as one story:

Admin Login -> Register Donor -> Create Campaign -> Record Donation -> Generate Receipt -> Register Volunteers ->
Create Community Project -> Submit for Approval -> Assign Volunteers -> Create Milestones -> Record Expenses ->
Allocate Resources -> Record Beneficiary Assistance -> Update Project Impact -> View Dashboard -> Export Reports ->
Verify Audit Logs
"""
from tests.conftest import PASSWORD
from tests.helpers import d


def test_full_ngo_workflow(client, api, make_user, login, auth):
    from app.utils.enums import Role

    # 1. Admin login ----------------------------------------------------------------------------------------------
    admin_user = make_user(Role.SUPER_ADMIN, "admin@ngo.org")
    admin = login(admin_user.email, PASSWORD)
    me = api.get("/auth/me", admin, 200).json()
    assert me["role"] == "super_admin"
    finance = auth(Role.FINANCE_OFFICER)
    manager = auth(Role.NGO_MANAGER)

    # 2. Register donor ---------------------------------------------------------------------------------------------
    donor = api.donor(admin)

    # 3. Create campaign (draft -> active) ------------------------------------------------------------------------
    campaign = api.campaign(admin, goal="10000.00", activate=False)
    assert campaign["status"] == "draft"
    campaign = api.post(f"/campaigns/{campaign['id']}/activate", admin, expect=200).json()
    assert campaign["status"] == "active"

    # 4. Record donation -> campaign total ------------------------------------------------------------------------
    donation = api.donation(admin, donor["id"], campaign["id"], "2500.00", "TXN-1001").json()
    assert donation["status"] == "confirmed"
    assert api.get(f"/campaigns/{campaign['id']}", admin, 200).json()["raised_amount"] == "2500.00"

    # 5. Generate receipt -----------------------------------------------------------------------------------------
    receipt = api.post("/receipts", admin, {"donation_id": donation["id"]}, 201).json()
    assert receipt["receipt_number"].startswith("RCT-")
    assert api.post("/receipts", admin, {"donation_id": donation["id"]}).status_code == 409  # no duplicates
    pdf = client.get(f"/api/v1/receipts/{receipt['id']}/pdf", headers=admin)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")

    # 6. Register volunteers --------------------------------------------------------------------------------------
    vol1 = api.volunteer(admin, "Ravi Kumar", "ravi@example.org")
    vol2 = api.volunteer(admin, "Sita Devi", "sita@example.org")

    # 7-8. Create project, submit for approval, approve ------------------------------------------------------------
    project = api.project(manager, budget="5000.00", campaign_id=campaign["id"])
    assert project["status"] == "planning"
    assert api.post(f"/projects/{project['id']}/status", admin, {"status": "active"}).status_code == 422  # not approved yet
    api.post(f"/projects/{project['id']}/submit", manager, {"comments": "Please review"}, 201)
    api.post(f"/projects/{project['id']}/approve", admin, {"comments": "Looks good"}, 200)
    api.post(f"/projects/{project['id']}/status", admin, {"status": "active"}, 200)
    history = api.get(f"/projects/{project['id']}/approvals", admin, 200).json()
    assert [h["action"] for h in history] == ["submitted", "approved"]

    # 9. Assign volunteers ----------------------------------------------------------------------------------------
    a1 = api.post("/assignments", admin, {
        "volunteer_id": vol1["id"], "project_id": project["id"], "responsibility": "Site coordinator",
        "start_date": d(-10), "end_date": d(60)}, 201).json()
    api.post("/assignments", admin, {
        "volunteer_id": vol2["id"], "project_id": project["id"], "responsibility": "Teaching assistant",
        "start_date": d(-10), "end_date": d(60)}, 201)
    api.post("/attendance", admin, {"assignment_id": a1["id"], "attendance_date": d(-2), "hours": "6.5"}, 201)
    api.post("/attendance", admin, {"assignment_id": a1["id"], "attendance_date": d(-1), "hours": "4"}, 201)
    assert api.get(f"/assignments/{a1['id']}", admin, 200).json()["hours_completed"] == "10.50"

    # 10. Milestones and tasks ------------------------------------------------------------------------------------
    ms = api.post("/milestones", manager, {"project_id": project["id"], "title": "Foundation", "due_date": d(30)}, 201).json()
    task = api.post("/tasks", manager, {"milestone_id": ms["id"], "title": "Pour concrete", "deadline": d(20), "priority": "high"}, 201).json()
    api.patch(f"/tasks/{task['id']}", manager, {"status": "completed"}, 200)
    assert api.get(f"/milestones/{ms['id']}", manager, 200).json()["status"] == "completed"

    # 11. Expenses: submit -> finance approves ---------------------------------------------------------------------
    exp = api.expense(manager, project["id"], "1200.00", "BILL-77").json()
    assert exp["status"] == "submitted"
    assert api.post(f"/expenses/{exp['id']}/approve", manager, {}).status_code == 403  # only finance
    api.post(f"/expenses/{exp['id']}/approve", finance, {"comment": "Verified"}, 200)
    util = api.get(f"/budgets/projects/{project['id']}/utilization", finance, 200).json()
    assert util["spent"] == "1200.00" and util["remaining"] == "3800.00" and util["is_overrun"] is False

    # 12. Allocate resources --------------------------------------------------------------------------------------
    res = api.resource(admin, "Food Package", qty=100, threshold=10)
    api.post("/resource-allocations", admin, {"resource_id": res["id"], "project_id": project["id"], "quantity": 40}, 201)
    assert api.get(f"/resources/{res['id']}", admin, 200).json()["quantity"] == 60

    # 13. Beneficiary assistance ----------------------------------------------------------------------------------
    ben = api.post("/beneficiaries", admin, {
        "full_name": "Lakshmi", "category": "family", "phone": "9876543210", "project_ids": [project["id"]]}, 201).json()
    api.post("/assistance", admin, {
        "beneficiary_id": ben["id"], "project_id": project["id"], "resource_id": res["id"], "assistance_type": "food package",
        "quantity": 5, "distribution_date": d(-1)}, 201)

    # 14. Impact update -------------------------------------------------------------------------------------------
    impact = api.post("/impact/updates", manager, {"project_id": project["id"], "notes": "First month"}, 201).json()
    assert impact["beneficiaries_served"] == 1 and impact["resources_distributed"] == 5
    assert impact["funds_utilized"] == "1200.00" and float(impact["volunteer_hours"]) == 10.5

    # 15. Dashboard -----------------------------------------------------------------------------------------------
    dash = api.get("/dashboard", admin, 200).json()
    assert dash["donations"]["confirmed_donations_amount"] == "2500.00"
    assert dash["campaigns"]["active_campaigns"] == 1
    assert dash["volunteers"]["total_volunteers"] == 2
    assert dash["projects"]["active_projects"] == 1
    assert dash["beneficiaries"]["total_beneficiaries_served"] == 1
    assert dash["resources"]["total_units_in_stock"] == 60

    # 16. Reports + CSV export ------------------------------------------------------------------------------------
    rep = api.get("/reports/donation-summary", admin, 200, group_by="campaign").json()
    assert rep["rows"][0]["total_amount"] == 2500.0
    csv_resp = client.get("/api/v1/reports/expenses", headers=admin, params={"export": "true"})
    assert csv_resp.status_code == 200 and csv_resp.headers["content-type"].startswith("text/csv")
    assert "expense_id" in csv_resp.text.splitlines()[0]
    for path in ("campaign-performance", "volunteer-contribution", "project-progress", "resource-distribution",
                 "beneficiary-impact", "budget-utilization"):
        assert api.get(f"/reports/{path}", admin).status_code == 200, path

    # 17. Audit logs ----------------------------------------------------------------------------------------------
    logs = api.get("/audit-logs", admin, 200, page_size=200).json()
    actions = {entry["action"] for entry in logs["items"]}
    for expected in ("donor.created", "campaign.active", "donation.created", "receipt.issued", "volunteer.registered",
                     "project.created", "project.approved", "assignment.created", "expense.approved", "resource.allocation",
                     "assistance.recorded", "impact.submitted"):
        assert expected in actions, f"missing audit action {expected}: {sorted(actions)}"
    entry = next(e for e in logs["items"] if e["action"] == "expense.approved")
    assert entry["actor_email"] == "finance_officer@ngo-demo.org" and entry["entity"] == "expense" and entry["details"]
