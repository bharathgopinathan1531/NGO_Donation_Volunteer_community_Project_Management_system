from datetime import date
from typing import Any, Iterable

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.utils.pagination import PaginationParams
from app.utils.sorting import SortParams


def snapshot(obj: Any, fields: Iterable[str]) -> dict:
    return {f: getattr(obj, f) for f in fields}


def diff(before: dict, after: dict) -> dict:
    """Return {field: {"from": old, "to": new}} for the fields that actually changed."""
    return {k: {"from": before.get(k), "to": after[k]} for k in after if before.get(k) != after[k]}


class AuditService:
    """Writes audit rows inside the caller's transaction, so an action and its audit trail commit (or roll back) together."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = AuditRepository(db)

    def log(self, actor: User | None, action: str, entity: str, entity_id: int | None, details: dict | None = None) -> AuditLog:
        entry = AuditLog(
            actor_id=actor.id if actor else None,
            actor_email=actor.email if actor else None,
            actor_role=actor.role.value if actor else None,
            action=action,
            entity=entity,
            entity_id=entity_id,
            details=jsonable_encoder(details) if details else None,
        )
        self.db.add(entry)
        return entry

    def list_logs(
        self, params: PaginationParams, sort: SortParams, *, actor_id: int | None, action: str | None, entity: str | None,
        entity_id: int | None, date_from: date | None, date_to: date | None,
    ):
        return self.repo.list_logs(
            params, sort, actor_id=actor_id, action=action, entity=entity, entity_id=entity_id, date_from=date_from, date_to=date_to
        )
