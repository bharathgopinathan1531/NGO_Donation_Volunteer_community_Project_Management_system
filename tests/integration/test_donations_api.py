from app.utils.enums import Role
from tests.helpers import d


def campaign_total(api, h, cid):
    return api.get(f"/campaigns/{cid}", h, 200).json()["raised_amount"]


def test_record_donation_updates_total(api, auth):
    h = auth(Role.FINANCE_OFFICER)
    donor, camp = api.donor(auth(Role.NGO_MANAGER)), api.campaign(auth(Role.NGO_MANAGER))
    r = api.donation(h, donor["id"], camp["id"], "1250.75", "UTR-1")
    assert r.status_code == 201 and r.json()["status"] == "confirmed" and r.json()["recorded_by"]
    assert campaign_total(api, h, camp["id"]) == "1250.75"


def test_non_positive_and_malformed_amounts_rejected(api, admin):
    donor, camp = api.donor(admin), api.campaign(admin)
    for bad in ("0", "-10", "abc", "10.999"):
        assert api.donation(admin, donor["id"], camp["id"], bad, f"B-{bad}").status_code == 422, bad
    assert campaign_total(api, admin, camp["id"]) == "0.00"


def test_duplicate_reference_conflicts(api, admin):
    donor, camp = api.donor(admin), api.campaign(admin)
    assert api.donation(admin, donor["id"], camp["id"], ref="DUP-1").status_code == 201
    assert api.donation(admin, donor["id"], camp["id"], ref="DUP-1").status_code == 409
    assert api.donation(admin, donor["id"], camp["id"], ref="  DUP-1  ").status_code == 409  # whitespace does not bypass it
    assert campaign_total(api, admin, camp["id"]) == "500.00"


def test_closed_and_inactive_campaigns_refuse_donations(api, admin):
    donor = api.donor(admin)
    done = api.campaign(admin, "Done")
    api.post(f"/campaigns/{done['id']}/close", admin, expect=200)
    draft = api.campaign(admin, "Draft", activate=False)
    paused = api.campaign(admin, "Paused")
    api.post(f"/campaigns/{paused['id']}/pause", admin, expect=200)
    for i, c in enumerate((done, draft, paused)):
        assert api.donation(admin, donor["id"], c["id"], ref=f"C-{i}").status_code == 422


def test_future_dated_and_bad_status_rejected(api, admin):
    donor, camp = api.donor(admin), api.campaign(admin)
    assert api.donation(admin, donor["id"], camp["id"], ref="F-1", donation_date=d(5)).status_code == 422
    assert api.donation(admin, donor["id"], camp["id"], ref="F-2", status="refunded").status_code == 422


def test_unknown_references_are_404(api, admin):
    donor, camp = api.donor(admin), api.campaign(admin)
    assert api.donation(admin, 9999, camp["id"], ref="N-1").status_code == 404
    assert api.donation(admin, donor["id"], 9999, ref="N-2").status_code == 404


def test_pending_confirm_cancel_reverse_refund_flow_keeps_totals_consistent(api, admin):
    donor, camp = api.donor(admin), api.campaign(admin)
    cid = camp["id"]
    p = api.donation(admin, donor["id"], cid, "100", "T-1", status="pending").json()
    assert campaign_total(api, admin, cid) == "0.00"
    assert api.post(f"/donations/{p['id']}/confirm", admin, expect=200).json()["status"] == "confirmed"
    assert campaign_total(api, admin, cid) == "100.00"
    assert api.post(f"/donations/{p['id']}/confirm", admin).status_code == 422  # already confirmed
    assert api.post(f"/donations/{p['id']}/reverse", admin, {"reason": "bounced cheque"}, 200).json()["status"] == "reversed"
    assert campaign_total(api, admin, cid) == "0.00"
    assert api.post(f"/donations/{p['id']}/refund", admin).status_code == 422  # terminal

    r = api.donation(admin, donor["id"], cid, "40", "T-2").json()
    api.donation(admin, donor["id"], cid, "60", "T-3")
    api.post(f"/donations/{r['id']}/refund", admin, {"reason": "donor request"}, 200)
    assert campaign_total(api, admin, cid) == "60.00"
    c = api.donation(admin, donor["id"], cid, "5", "T-4", status="pending").json()
    api.post(f"/donations/{c['id']}/cancel", admin, expect=200)
    assert campaign_total(api, admin, cid) == "60.00"


def test_confirmed_donation_financials_are_immutable(api, admin):
    donor, camp = api.donor(admin), api.campaign(admin)
    don = api.donation(admin, donor["id"], camp["id"], "100", "I-1").json()
    assert api.patch(f"/donations/{don['id']}", admin, {"amount": "999"}).status_code == 422
    assert api.patch(f"/donations/{don['id']}", admin, {"notes": "thank-you sent"}, 200).json()["notes"] == "thank-you sent"
    pend = api.donation(admin, donor["id"], camp["id"], "100", "I-2", status="pending").json()
    assert api.patch(f"/donations/{pend['id']}", admin, {"amount": "75.50"}, 200).json()["amount"] == "75.50"


def test_permissions(api, auth):
    mgr = auth(Role.NGO_MANAGER)
    donor, camp = api.donor(mgr), api.campaign(mgr)
    for role in (Role.VOLUNTEER, Role.DONOR, Role.VOLUNTEER_COORDINATOR):
        assert api.donation(auth(role), donor["id"], camp["id"], ref=f"P-{role.value}").status_code == 403, role
    assert api.donation(None, donor["id"], camp["id"], ref="anon").status_code == 401


def test_donor_sees_only_their_own_donations(api, auth, admin):
    camp = api.campaign(admin)
    mine_h = api.signup("mine@example.org", "donor")
    mine = api.get("/donors/me", mine_h, 200).json()
    other = api.donor(admin, "Other", "other@example.org")
    api.donation(admin, mine["id"], camp["id"], "10", "O-1")
    theirs = api.donation(admin, other["id"], camp["id"], "20", "O-2").json()
    page = api.get("/donations", mine_h, 200).json()
    assert page["total"] == 1 and page["items"][0]["amount"] == "10.00"
    assert api.get("/donations", mine_h, donor_id=other["id"]).status_code == 403
    assert api.get(f"/donations/{theirs['id']}", mine_h).status_code == 403


def test_filters_and_sorting(api, admin):
    donor, camp = api.donor(admin), api.campaign(admin)
    api.donation(admin, donor["id"], camp["id"], "10", "L-1", method="cash")
    api.donation(admin, donor["id"], camp["id"], "30", "L-2", method="upi")
    api.donation(admin, donor["id"], camp["id"], "20", "L-3", status="pending")
    assert api.get("/donations", admin, method="upi").json()["total"] == 1
    assert api.get("/donations", admin, status="pending").json()["total"] == 1
    assert api.get("/donations", admin, search="L-2").json()["total"] == 1
    amounts = [i["amount"] for i in api.get("/donations", admin, sort_by="amount", order="desc").json()["items"]]
    assert amounts == ["30.00", "20.00", "10.00"]
    assert api.get("/donations", admin, campaign_id=camp["id"], date_from=d(-5), date_to=d(0)).json()["total"] == 3
