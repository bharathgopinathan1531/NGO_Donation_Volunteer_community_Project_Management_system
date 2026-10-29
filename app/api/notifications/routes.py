from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_permissions
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import Message, Page
from app.schemas.notification import GenerationResult, NotificationOut, UnreadCount
from app.services.notification_service import NotificationService
from app.utils.enums import NotificationType
from app.utils.pagination import PaginationParams, build_page, pagination_params

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=Page[NotificationOut], summary="My notifications")
def list_mine(
    unread_only: bool = False, type: NotificationType | None = None, params: PaginationParams = Depends(pagination_params),
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    items, total = NotificationService(db).list_mine(user, params, unread_only=unread_only, type=type)
    return build_page([NotificationOut.model_validate(i) for i in items], total, params)


@router.get("/unread-count", response_model=UnreadCount)
def unread_count(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return UnreadCount(unread=NotificationService(db).unread_count(user))


@router.post("/read-all", response_model=Message, summary="Mark all my notifications as read")
def read_all(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = NotificationService(db).mark_all_read(user)
    return Message(message=f"{n} notification(s) marked as read")


@router.post("/generate", response_model=GenerationResult, summary="Scan for deadlines, overdue milestones, low stock, pending expenses, closing campaigns, overruns")
def generate(_: User = Depends(require_permissions(Permission.NOTIFICATIONS_MANAGE)), db: Session = Depends(get_db)):
    return NotificationService(db).generate_scheduled()


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return NotificationService(db).mark_read(user, notification_id, True)


@router.post("/{notification_id}/unread", response_model=NotificationOut)
def mark_unread(notification_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return NotificationService(db).mark_read(user, notification_id, False)
