"""Small factory layer so tests read like the business workflow they exercise."""
from datetime import date, timedelta

TODAY = date.today()
P = "/api/v1"


def d(offset: int = 0) -> str:
    return (TODAY + timedelta(days=offset)).isoformat()


class Api:
    def __init__(self, client):
        self.c = client

    # -- generic ------------------------------------------------------------
    def post(self, path, h, json=None, expect=None):
        r = self.c.post(f"{P}{path}", json=json, headers=h)
        if expect:
            assert r.status_code == expect, f"{path}: {r.status_code} {r.text}"
        return r

    def get(self, path, h, expect=None, **params):
        r = self.c.get(f"{P}{path}", headers=h, params=params)
        if expect:
            assert r.status_code == expect, f"{path}: {r.status_code} {r.text}"
        return r

    def patch(self, path, h, json=None, expect=None):
        r = self.c.patch(f"{P}{path}", json=json, headers=h)
        if expect:
            assert r.status_code == expect, f"{path}: {r.status_code} {r.text}"
        return r

    def put(self, path, h, json=None, expect=None):
        r = self.c.put(f"{P}{path}", json=json, headers=h)
        if expect:
            assert r.status_code == expect, f"{path}: {r.status_code} {r.text}"
        return r

    # -- donors / campaigns / donations -------------------------------------
    def donor(self, h, name="Asha Rao", email="asha@example.org", **kw) -> dict:
        return self.post("/donors", h, {"name": name, "email": email, "donor_type": "individual", **kw}, 201).json()

    def campaign(self, h, title="Clean Water Drive", goal="10000.00", activate=True, **kw) -> dict:
        body = {"title": title, "goal_amount": goal, "category": "health", "start_date": d(-30), "end_date": d(60), **kw}
        c = self.post("/campaigns", h, body, 201).json()
        if activate:
            c = self.post(f"/campaigns/{c['id']}/activate", h, expect=200).json()
        return c

    def donation(self, h, donor_id, campaign_id, amount="500.00", ref="REF-001", status="confirmed", **kw):
        body = {
            "donor_id": donor_id, "campaign_id": campaign_id, "amount": amount, "donation_date": d(-1), "method": "bank_transfer",
            "reference_number": ref, "status": status, **kw,
        }
        return self.post("/donations", h, body)

    # -- volunteers / projects ----------------------------------------------
    def volunteer(self, h, name="Ravi Kumar", email="ravi@example.org", **kw) -> dict:
        body = {"full_name": name, "email": email, "skills": ["teaching", "first aid"], "availability": "weekends", **kw}
        return self.post("/volunteers", h, body, 201).json()

    def project(self, h, name="Village School Renovation", budget="5000.00", **kw) -> dict:
        body = {
            "name": name, "objectives": "Renovate the school", "location": "Hyderabad", "start_date": d(-20), "end_date": d(120),
            "budget": budget, **kw,
        }
        return self.post("/projects", h, body, 201).json()

    def approved_project(self, submitter_h, approver_h, activate=True, **kw) -> dict:
        p = self.project(submitter_h, **kw)
        self.post(f"/projects/{p['id']}/submit", submitter_h, {"comments": "ready"}, 201)
        self.post(f"/projects/{p['id']}/approve", approver_h, {"comments": "ok"}, 200)
        if activate:
            self.post(f"/projects/{p['id']}/status", approver_h, {"status": "active"}, 200)
        return self.get(f"/projects/{p['id']}", approver_h, 200).json()

    def expense(self, h, project_id, amount="1000.00", ref="BILL-1", **kw):
        body = {
            "project_id": project_id, "category": "materials", "amount": amount, "expense_date": d(-2),
            "description": "Cement and paint", "receipt_reference": ref, **kw,
        }
        return self.post("/expenses", h, body)

    def resource(self, h, name="Food Package", qty=100, threshold=10, **kw) -> dict:
        body = {"name": name, "category": "food_package", "initial_quantity": qty, "low_stock_threshold": threshold, "unit": "box", **kw}
        return self.post("/resources", h, body, 201).json()

    # -- self-service accounts ----------------------------------------------
    def signup(self, email, role="volunteer", password="Passw0rd1", name="Self Registered"):
        """Register through the public endpoint and return auth headers."""
        self.post("/auth/register", None, {"email": email, "full_name": name, "password": password, "role": role}, 201)
        r = self.post("/auth/login", None, {"email": email, "password": password}, 200)
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    def volunteer_login(self, email="selfvol@example.org"):
        h = self.signup(email, "volunteer")
        profile = self.post("/volunteers/me", h, {"full_name": "Self Vol", "email": email, "skills": ["cooking"]}, 201).json()
        return h, profile
