from app.utils.enums import Role


def test_overview_and_sections(api, auth, admin):
    mgr = auth(Role.NGO_MANAGER)
    donor = api.donor(admin)
    camp = api.campaign(admin, goal="1000.00")
    api.donation(admin, donor["id"], camp["id"], "250.00", "D-1")
    p = api.approved_project(mgr, admin)
    api.resource(mgr, "Dash Item", 3, 10)
    overview = api.get("/dashboard", admin, 200).json()
    assert overview
    for section in ("donations", "campaigns", "volunteers", "projects", "expenses", "resources", "beneficiaries"):
        assert api.get(f"/dashboard/{section}", admin, 200).status_code == 200, section
    don = api.get("/dashboard/donations", admin, 200).json()
    assert "250.00" in str(don)
    assert p


def test_permissions(api, auth):
    for role in (Role.VOLUNTEER, Role.DONOR):
        assert api.get("/dashboard", auth(role)).status_code == 403, role
    for role in (Role.NGO_MANAGER, Role.FINANCE_OFFICER, Role.VOLUNTEER_COORDINATOR):
        assert api.get("/dashboard", auth(role)).status_code == 200, role
