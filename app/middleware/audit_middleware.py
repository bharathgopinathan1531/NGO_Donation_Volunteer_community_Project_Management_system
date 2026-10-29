"""Security audit trail for rejected mutations.

Successful business actions are audited transactionally inside the services. This middleware complements that by
recording *denied* write attempts (401/403 on POST/PUT/PATCH/DELETE) so administrators can review suspicious activity.
"""
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.jwt import ACCESS, decode_token
from app.models.audit_log import AuditLog
from app.models.user import User

logger = logging.getLogger("app.audit")
MUTATING = {"POST", "PUT", "PATCH", "DELETE"}


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.method in MUTATING and response.status_code in (401, 403):
            self._record_denied(request, response.status_code)
        return response

    @staticmethod
    def _record_denied(request: Request, status_code: int) -> None:
        factory = getattr(request.app.state, "session_factory", None)
        if factory is None:
            return
        db = factory()
        try:
            actor = None
            auth = request.headers.get("authorization", "")
            if auth.lower().startswith("bearer "):
                try:
                    actor = db.get(User, int(decode_token(auth[7:], ACCESS)["sub"]))
                except Exception:  # invalid / expired token -> anonymous
                    actor = None
            db.add(
                AuditLog(
                    actor_id=actor.id if actor else None,
                    actor_email=actor.email if actor else None,
                    actor_role=actor.role.value if actor else None,
                    action="security.access_denied",
                    entity="http",
                    details={"method": request.method, "path": request.url.path, "status": status_code,
                             "request_id": getattr(request.state, "request_id", None)},
                )
            )
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Could not record access-denied audit entry")
        finally:
            db.close()
