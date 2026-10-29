from app.utils.enums import Role


def setup_donation(api, h, amount="300.00", ref="RC-1", status="confirmed"):
    donor, camp = api.donor(h), api.campaign(h)
    don = api.donation(h, donor["id"], camp["id"], amount, ref, status=status).json()
    return donor, camp, don


def test_receipt_generation_for_confirmed_donation(api, admin):
    donor, camp, don = setup_donation(api, admin)
    r = api.post("/receipts", admin, {"donation_id": don["id"]}, 201).json()
    assert r["status"] == "issued" and r["amount"] == "300.00" and r["donor_id"] == donor["id"]
    assert r["metadata"]["campaign_title"] == camp["title"] and r["metadata"]["donation_reference"] == "RC-1"
    assert api.get(f"/receipts/{r['id']}", admin, 200).json()["receipt_number"] == r["receipt_number"]
    assert api.get(f"/receipts/by-number/{r['receipt_number']}", admin, 200).json()["id"] == r["id"]
    assert api.get(f"/donations/{don['id']}/receipt", admin, 200).json()["id"] == r["id"]


def test_duplicate_receipt_prevented(api, admin):
    _, _, don = setup_donation(api, admin)
    api.post("/receipts", admin, {"donation_id": don["id"]}, 201)
    assert api.post("/receipts", admin, {"donation_id": don["id"]}).status_code == 409
    assert api.get("/receipts", admin, 200).json()["total"] == 1


def test_pending_cancelled_and_unknown_donations_get_no_receipt(api, admin):
    _, _, pending = setup_donation(api, admin, ref="RC-P", status="pending")
    assert api.post("/receipts", admin, {"donation_id": pending["id"]}).status_code == 422
    api.post(f"/donations/{pending['id']}/cancel", admin, expect=200)
    assert api.post("/receipts", admin, {"donation_id": pending["id"]}).status_code == 422
    assert api.post("/receipts", admin, {"donation_id": 9999}).status_code == 404
    assert api.get(f"/donations/{pending['id']}/receipt", admin).status_code == 404


def test_refund_and_reversal_void_the_receipt(api, admin):
    donor, camp, don = setup_donation(api, admin)
    r = api.post("/receipts", admin, {"donation_id": don["id"]}, 201).json()
    api.post(f"/donations/{don['id']}/refund", admin, {"reason": "duplicate payment"}, 200)
    voided = api.get(f"/receipts/{r['id']}", admin, 200).json()
    assert voided["status"] == "void" and voided["void_reason"] == "duplicate payment" and voided["voided_at"]
    assert api.get("/receipts", admin, 200, status="void").json()["total"] == 1
    assert api.post("/receipts", admin, {"donation_id": don["id"]}).status_code == 422
    pdf = api.c.get(f"/api/v1/receipts/{r['id']}/pdf", headers=admin)
    assert pdf.status_code == 200 and b"VOID" in pdf.content


def test_receipts_by_donor(api, admin):
    donor, camp, d1 = setup_donation(api, admin, ref="BD-1")
    d2 = api.donation(admin, donor["id"], camp["id"], "50", "BD-2").json()
    other = api.donor(admin, "Other", "other@example.org")
    d3 = api.donation(admin, other["id"], camp["id"], "70", "BD-3").json()
    for x in (d1, d2, d3):
        api.post("/receipts", admin, {"donation_id": x["id"]}, 201)
    page = api.get(f"/receipts/donor/{donor['id']}", admin, 200).json()
    assert page["total"] == 2 and {r["donor_id"] for r in page["items"]} == {donor["id"]}
    assert api.get("/receipts", admin, 200, donor_id=other["id"]).json()["total"] == 1


def test_donor_can_read_only_own_receipts(api, admin):
    camp = api.campaign(admin)
    me = api.signup("rd@example.org", "donor")
    mine = api.get("/donors/me", me, 200).json()
    other = api.donor(admin, "Other", "o@example.org")
    r_mine = api.post("/receipts", admin, {"donation_id": api.donation(admin, mine["id"], camp["id"], "10", "DR-1").json()["id"]}, 201).json()
    r_other = api.post("/receipts", admin, {"donation_id": api.donation(admin, other["id"], camp["id"], "20", "DR-2").json()["id"]}, 201).json()
    assert api.get("/receipts", me, 200).json()["total"] == 1
    assert api.get(f"/receipts/{r_mine['id']}", me, 200)
    assert api.get(f"/receipts/{r_other['id']}", me).status_code == 403
    assert api.get(f"/receipts/donor/{other['id']}", me).status_code == 403
    assert api.get(f"/receipts/{r_other['id']}/pdf", me).status_code == 403
    assert api.get(f"/receipts/{r_mine['id']}/pdf", me).status_code == 200
    assert api.post("/receipts", me, {"donation_id": 1}).status_code == 403


def test_other_roles_cannot_issue_or_read(api, auth, admin):
    _, _, don = setup_donation(api, admin)
    assert api.post("/receipts", auth(Role.VOLUNTEER), {"donation_id": don["id"]}).status_code == 403
    assert api.post("/receipts", auth(Role.VOLUNTEER_COORDINATOR), {"donation_id": don["id"]}).status_code == 403
    assert api.post("/receipts", auth(Role.FINANCE_OFFICER), {"donation_id": don["id"]}, 201)
    assert api.get("/receipts", auth(Role.VOLUNTEER)).status_code == 403
