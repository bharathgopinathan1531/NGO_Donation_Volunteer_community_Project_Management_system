from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import require_permissions
from app.core.exceptions import NotFoundError
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.audit_log import AuditLogOut
from app.schemas.common import Page
from app.services.audit_service import AuditService
from app.utils.pagination import PaginationParams, build_page, pagination_params
from app.utils.sorting import SortParams, sort_params

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])
reader = require_permissions(Permission.AUDIT_READ)


@router.get("", response_model=Page[AuditLogOut], summary="Audit trail (actor, action, entity, timestamp, change details)")
def list_logs(
    actor_id: int | None = None, action: str | None = None, entity: str | None = None, entity_id: int | None = None,
    date_from: date | None = None, date_to: date | None = None,
    params: PaginationParams = Depends(pagination_params), sort: SortParams = Depends(sort_params),
    _: User = Depends(reader), db: Session = Depends(get_db),
):
    items, total = AuditService(db).list_logs(
        params, sort, actor_id=actor_id, action=action, entity=entity, entity_id=entity_id, date_from=date_from, date_to=date_to
    )
    return build_page([AuditLogOut.model_validate(i) for i in items], total, params)


@router.get("/{log_id}", response_model=AuditLogOut)
def get_log(log_id: int, _: User = Depends(reader), db: Session = Depends(get_db)):
    log = AuditService(db).repo.get(log_id)
    if not log:
        raise NotFoundError("Audit log entry not found")
    return log
