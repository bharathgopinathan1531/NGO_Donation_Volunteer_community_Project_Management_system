from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel
from app.utils.enums import NotificationType


class NotificationOut(ORMModel):
    id: int
    type: NotificationType
    title: str
    message: str
    entity: str | None
    entity_id: int | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime


class UnreadCount(BaseModel):
    unread: int


class GenerationResult(BaseModel):
    created: int
    by_type: dict[str, int]
