from datetime import date

from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.repositories import BaseRepository
from app.utils.filtering import apply_date_range, apply_equals
from app.utils.pagination import PaginationParams, paginate
from app.utils.sorting import SortParams, apply_sorting


class AuditRepository(BaseRepository[AuditLog]):
    model = AuditLog

    def list_logs(
        self, params: PaginationParams, sort: SortParams, *, actor_id: int | None = None, action: str | None = None,
        entity: str | None = None, entity_id: int | None = None, date_from: date | None = None, date_to: date | None = None,
    ):
        stmt = apply_equals(select(AuditLog), AuditLog, actor_id=actor_id, action=action, entity=entity, entity_id=entity_id)
        stmt = apply_date_range(stmt, AuditLog.created_at, date_from, date_to)
        stmt = apply_sorting(stmt, AuditLog, sort, {"id", "created_at", "action", "entity"}, default="id", default_order="desc")
        return paginate(self.db, stmt, params)
