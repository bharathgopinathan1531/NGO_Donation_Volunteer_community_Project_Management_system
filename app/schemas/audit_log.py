from datetime import datetime
from typing import Any

from app.schemas.common import ORMModel


class AuditLogOut(ORMModel):
    id: int
    actor_id: int | None
    actor_email: str | None
    actor_role: str | None
    action: str
    entity: str
    entity_id: int | None
    details: dict[str, Any] | None
    created_at: datetime
