from sqlalchemy import func, select, update

from app.models.notification import Notification
from app.repositories import BaseRepository
from app.utils.date_utils import utcnow
from app.utils.enums import NotificationType
from app.utils.pagination import PaginationParams, paginate


class NotificationRepository(BaseRepository[Notification]):
    model = Notification

    def exists(self, user_id: int, dedupe_key: str) -> bool:
        stmt = select(Notification.id).where(Notification.user_id == user_id, Notification.dedupe_key == dedupe_key).limit(1)
        return self.db.scalar(stmt) is not None

    def list_for_user(self, user_id: int, params: PaginationParams, *, unread_only: bool = False, type: NotificationType | None = None):
        stmt = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            stmt = stmt.where(Notification.is_read.is_(False))
        if type:
            stmt = stmt.where(Notification.type == type)
        return paginate(self.db, stmt.order_by(Notification.id.desc()), params)

    def unread_count(self, user_id: int) -> int:
        return self.db.scalar(select(func.count()).select_from(Notification).where(Notification.user_id == user_id, Notification.is_read.is_(False))) or 0

    def mark_all_read(self, user_id: int) -> int:
        result = self.db.execute(
            update(Notification).where(Notification.user_id == user_id, Notification.is_read.is_(False)).values(is_read=True, read_at=utcnow())
        )
        return result.rowcount or 0
