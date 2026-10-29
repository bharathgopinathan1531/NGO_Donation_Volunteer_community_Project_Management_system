# NGO Donation, Volunteer & Community Project Management System

FastAPI backend covering all 22 levels of the assignment: authentication & RBAC, donors, campaigns, donations & receipts,
volunteers, assignments & attendance, projects with an approval workflow, milestones & tasks, budgets & expenses,
inventory, beneficiaries, impact tracking, notifications, dashboards, reports and an audit trail.

**Stack:** FastAPI · Pydantic v2 · SQLAlchemy 2 · Alembic · JWT (PyJWT) · bcrypt · pytest · Docker (PostgreSQL)

## Quick start (local, SQLite)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # for a zero-setup run use DATABASE_URL=sqlite:///./ngo_dev.db
alembic upgrade head            # or skip: in development the app auto-creates tables
python -m scripts.create_super_admin
uvicorn app.main:app --reload
```

Swagger UI: http://localhost:8000/docs · Health: `/health`, `/health/ready`

Optional demo data: `python -m scripts.seed_demo_data` (creates manager/finance/coordinator users, password `Demo@12345`).

## Docker (PostgreSQL)

```bash
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(48))")
export SUPER_ADMIN_PASSWORD='Str0ng@Passw0rd'
docker compose up --build
```
The container runs `alembic upgrade head`, ensures the super admin exists, then starts uvicorn on port 8000.
Production mode refuses to start with a weak `SECRET_KEY`, `DEBUG=true` or `EXPOSE_RESET_TOKEN=true`.

## Tests

```bash
pytest                       # unit + integration (SQLite in memory)
pytest tests/unit            # services/business rules
pytest tests/integration     # HTTP-level, incl. the mandatory end-to-end demo
```
`tests/integration/test_end_to_end_demo.py` runs the required flow: donor → campaign → donation → receipt → project →
approval → volunteer assignment → attendance → milestone/task → expense approval → resource allocation → beneficiary
assistance → impact → dashboard/report → audit log.

## Architecture

`routes → services → repositories → models/schemas`. Repositories never commit; services own the transaction
(`transaction(db)`), and audit rows are written in the same transaction as the action they describe.

```
app/
  api/<domain>/routes.py   HTTP layer (25 routers, /api/v1)
  services/                business rules, transactions, audit, notifications
  repositories/            queries only
  models/ schemas/         SQLAlchemy tables (25) / Pydantic DTOs
  core/                    config, security, jwt, permissions, dependencies, error handlers
  middleware/              request id, audit of denied (401/403) mutations
alembic/                   migrations (0001 = full schema)
tests/  scripts/  postman/
```

## Roles & permissions

| Role | Can do |
|---|---|
| `super_admin` | Everything, incl. budget override on expenses and user management |
| `ngo_manager` | Donors, campaigns, donations, volunteers, projects (create/approve), milestones, tasks, expenses (submit), budgets, resources, beneficiaries (incl. sensitive fields), impact, notifications, reports, audit log |
| `finance_officer` | Donations & receipts, expense approval/reimbursement, budgets, finance reports, read-only projects/resources |
| `volunteer_coordinator` | Volunteers, assignments, attendance, submit projects, milestones/tasks, beneficiaries (redacted), operations reports |
| `volunteer` | Own profile, own assignments, assigned projects, update own tasks |
| `donor` | Own donor profile, donations and receipts |

Authorisation is permission-based (`app/core/permissions.py`); routes declare `require_permissions(...)`.
Self-registration (`/auth/register`) only allows `volunteer` and `donor`.

## Key business rules

- **Auth:** access + refresh JWTs; refresh tokens are stored and rotated (single use); password reset tokens are stored hashed
  and `forgot-password` answers identically for unknown emails; deactivating a user revokes their refresh tokens.
- **Donations:** pending → confirmed → refunded/reversed; confirming adds to the campaign `raised_amount`, refund/reverse
  deducts it and voids the receipt (row-locked updates). Duplicate reference numbers are rejected. One receipt per donation.
- **Campaigns:** draft → active ⇄ paused → completed/cancelled; donations only to active campaigns.
- **Projects:** planning → *approval workflow* → approved → active → completed/cancelled. Activation needs an approval;
  completion needs all milestones done; closing a project closes its live assignments; a non-admin cannot approve their own submission.
- **Milestones/tasks:** milestone status & progress derive from tasks; task status and progress stay in sync (completed ⇔ 100%).
  Volunteers may only update status/progress of tasks assigned to them.
- **Expenses:** finance/super-admin approval only; budget check against project (and campaign) budget; only super admin may
  `override_budget`; submitters cannot approve their own; duplicates detected; receipt reference or attachment required.
- **Inventory:** every change goes through one ledger-writing path with row locks; stock never goes below zero;
  allocation reduces stock; beneficiary distribution cannot exceed the project's allocation; low-stock notifications are deduplicated.
- **Beneficiaries:** phone/address/national ID/notes are redacted unless the caller has `beneficiaries:sensitive`, and are never written to audit details.
- **Notifications:** `POST /notifications/generate` (schedule it with cron) scans deadlines, overdue milestones, closing campaigns,
  low stock, pending expenses and budget overruns; a unique key prevents duplicates.
- **Reports:** filter/sort/paginate every report; `?export=true` returns CSV (formula-injection safe).
- **Errors:** uniform body `{"error": {"code", "detail", "request_id", ...}}`; every response carries `X-Request-ID`.

## Endpoint overview (`/api/v1`)

`/auth` · `/users` · `/donors` · `/campaigns` · `/donations` · `/receipts` · `/volunteers` · `/assignments` · `/attendance` ·
`/projects` (+ `/submit`, `/approve`, `/reject`, `/status`, `/milestones`) · `/approvals/pending` · `/milestones` · `/tasks` ·
`/expenses` · `/budgets` · `/resources` · `/resource-allocations` · `/beneficiaries` · `/assistance` · `/impact` ·
`/notifications` · `/dashboard` · `/reports` · `/audit-logs`. The full list with summaries is in Swagger (`/docs`).

## Postman

Import `postman/ngo_management_collection.json`, then run the folder **End-to-end demo flow** in order with the Collection
Runner. Tokens and ids are saved to collection variables automatically (default base URL `http://localhost:8000`,
admin `admin@ngo.org` / `Admin@12345` — change to match your `.env`).

## Assumptions

- Currency is a single unspecified unit; amounts are `Decimal` (2 dp, half-up) with DB CHECK constraints.
- Timestamps are stored as naive UTC. Receipt PDFs use a dependency-free generator.
- Emails are written to templates in `app/templates/emails`; no SMTP is wired in (the reset token is returned only when `EXPOSE_RESET_TOKEN=true`).
