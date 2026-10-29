from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.core.security import hash_password
from app.db.session import transaction
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate
from app.services.audit_service import AuditService, diff
from app.services.auth_service import render_email, send_email
from app.utils.enums import Role
from app.utils.pagination import PaginationParams
from app.utils.sorting import SortParams


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UserRepository(db)
        self.tokens = RefreshTokenRepository(db)
        self.audit = AuditService(db)

    def _get(self, user_id: int) -> User:
        user = self.repo.get(user_id)
        if not user:
            raise NotFoundError("User not found")
        return user

    def get(self, user_id: int) -> User:
        return self._get(user_id)

    def list_users(self, params: PaginationParams, sort: SortParams, *, role: Role | None, is_active: bool | None, search: str | None):
        return self.repo.list_users(params, sort, role=role, is_active=is_active, search=search)

    def create(self, actor: User, data: UserCreate) -> User:
        email = data.email.lower()
        if self.repo.get_by_email(email):
            raise ConflictError("An account with this email already exists")
        with transaction(self.db):
            user = self.repo.add(
                User(email=email, full_name=data.full_name.strip(), hashed_password=hash_password(data.password), role=data.role, is_active=True)
            )
            self.audit.log(actor, "user.created", "user", user.id, {"email": email, "role": data.role.value})
        return user

    def update(self, actor: User, user_id: int, data: UserUpdate) -> User:
        with transaction(self.db):
            user = self._get(user_id)
            before = {"full_name": user.full_name, "role": user.role}
            changes = data.model_dump(exclude_unset=True, exclude_none=True)
            if "role" in changes and changes["role"] != user.role:
                if user.id == actor.id:
                    raise BusinessRuleError("You cannot change your own role")
                if user.role == Role.SUPER_ADMIN and self._active_super_admins() <= 1:
                    raise BusinessRuleError("Cannot change the role of the last active super admin")
            for k, v in changes.items():
                setattr(user, k, v)
            self.audit.log(actor, "user.updated", "user", user.id, diff(before, {"full_name": user.full_name, "role": user.role}))
        return user

    def _active_super_admins(self) -> int:
        return self.db.scalar(select(func.count(User.id)).where(User.role == Role.SUPER_ADMIN, User.is_active.is_(True))) or 0

    def set_active(self, actor: User, user_id: int, active: bool) -> User:
        with transaction(self.db):
            user = self._get(user_id)
            if user.is_active == active:
                raise BusinessRuleError(f"User is already {'active' if active else 'deactivated'}")
            if not active:
                if user.id == actor.id:
                    raise BusinessRuleError("You cannot deactivate your own account")
                if user.role == Role.SUPER_ADMIN and self._active_super_admins() <= 1:
                    raise BusinessRuleError("Cannot deactivate the last active super admin")
                self.tokens.revoke_all_for_user(user.id)
            user.is_active = active
            self.audit.log(actor, "user.activated" if active else "user.deactivated", "user", user.id)
        send_email(
            user.email, f"Your account has been {'activated' if active else 'deactivated'}",
            render_email("account_activation.html", name=user.full_name, email=user.email, state="activated" if active else "deactivated"),
        )
        return user
