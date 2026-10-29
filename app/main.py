import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router, health
from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import setup_logging
from app.db.session import SessionLocal
from app.middleware.audit_middleware import AuditMiddleware
from app.middleware.request_id import RequestIDMiddleware

logger = logging.getLogger("app")

DESCRIPTION = """
Backend for NGOs: donors, donations & receipts, fundraising campaigns, volunteers & assignments, community projects with
an approval workflow, milestones & tasks, expenses & budgets, resource inventory, beneficiaries, impact tracking,
notifications, dashboards, reports (CSV export) and audit logs.

**Auth:** `POST /api/v1/auth/login` -> copy the `access_token` -> click **Authorize** and paste it.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_for_production()
    setup_logging(settings.DEBUG)
    if settings.ENVIRONMENT.lower() == "development":
        # Developer convenience only. Production schema comes from `alembic upgrade head`.
        from app.db.init_db import create_tables, ensure_super_admin

        create_tables()
        with SessionLocal() as db:
            ensure_super_admin(db)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME, description=DESCRIPTION, version="1.0.0", lifespan=lifespan,
        docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json",
    )
    app.state.session_factory = SessionLocal  # used by AuditMiddleware (tests may replace it)

    # last added = outermost: request id wraps everything so audit entries can reference it
    app.add_middleware(AuditMiddleware)
    app.add_middleware(
        CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
    )
    app.add_middleware(RequestIDMiddleware)

    register_exception_handlers(app)
    app.include_router(health)
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
