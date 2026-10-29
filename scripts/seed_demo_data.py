"""Load a small demo data set by driving the real API in-process (so every business rule and audit entry applies).

Usage:  python -m scripts.seed_demo_data
Requires the super admin from .env (created automatically on start-up in development).
"""
from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.init_db import create_tables, ensure_super_admin
from app.db.session import SessionLocal
from app.main import create_app

P = "/api/v1"
PASSWORD = "Demo@12345"


def d(n: int) -> str:
    return (date.today() + timedelta(days=n)).isoformat()


def main() -> None:
    create_tables()
    with SessionLocal() as db:
        ensure_super_admin(db)
    with TestClient(create_app()) as c:
        def call(method, path, token=None, **kw):
            r = c.request(method, P + path, headers={"Authorization": f"Bearer {token}"} if token else None, **kw)
            if r.status_code >= 400:
                raise SystemExit(f"{method} {path} -> {r.status_code} {r.text}")
            return r.json()

        admin = call("POST", "/auth/login", json={"email": settings.SUPER_ADMIN_EMAIL, "password": settings.SUPER_ADMIN_PASSWORD})["access_token"]
        tokens = {}
        for key, role in (("manager", "ngo_manager"), ("finance", "finance_officer"), ("coordinator", "volunteer_coordinator")):
            email = f"{key}@ngo-demo.org"
            r = c.post(f"{P}/users", headers={"Authorization": f"Bearer {admin}"}, json={"email": email, "full_name": key.title(), "password": PASSWORD, "role": role})
            if r.status_code not in (201, 409):
                raise SystemExit(f"user {key}: {r.status_code} {r.text}")
            tokens[key] = call("POST", "/auth/login", json={"email": email, "password": PASSWORD})["access_token"]
        m, f = tokens["manager"], tokens["finance"]

        donor = call("POST", "/donors", m, json={"name": "Asha Rao", "email": "asha.donor@ngo-demo.org", "donor_type": "individual"})
        camp = call("POST", "/campaigns", m, json={"title": "Clean Water Drive", "category": "health", "description": "Wells for 5 villages", "goal_amount": "100000.00", "start_date": d(-5), "end_date": d(60)})
        call("POST", f"/campaigns/{camp['id']}/activate", m)
        call("POST", "/donations", f, json={"donor_id": donor["id"], "campaign_id": camp["id"], "amount": "25000.00", "method": "bank_transfer", "reference_number": "SEED-REF-1", "donation_date": d(-1), "status": "confirmed"})
        proj = call("POST", "/projects", m, json={"name": "Village Well Construction", "campaign_id": camp["id"], "budget": "60000.00", "start_date": d(0), "end_date": d(45), "location": "Warangal"})
        call("POST", f"/projects/{proj['id']}/submit", m, json={"comments": "Seed submission"})
        call("POST", f"/projects/{proj['id']}/approve", admin, json={"comments": "Seed approval"})
        call("POST", f"/projects/{proj['id']}/status", admin, json={"status": "active"})
        ms = call("POST", "/milestones", m, json={"project_id": proj["id"], "title": "Site survey", "due_date": d(10)})
        call("POST", "/tasks", m, json={"milestone_id": ms["id"], "title": "Survey the site", "deadline": d(7), "priority": "high"})
        call("POST", "/resources", m, json={"name": "Ration kits", "category": "food_package", "initial_quantity": 200, "low_stock_threshold": 20, "unit": "bag"})
    print("Demo data loaded. Logins (password %s): manager@ngo-demo.org, finance@ngo-demo.org, coordinator@ngo-demo.org" % PASSWORD)


if __name__ == "__main__":
    main()
