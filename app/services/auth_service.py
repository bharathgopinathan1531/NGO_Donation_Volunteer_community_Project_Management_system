import logging
from datetime import timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConflictError, ForbiddenError, UnauthorizedError
from app.core.jwt import REFRESH, create_access_token, create_refresh_token, decode_token
from app.core.permissions import SELF_REGISTRATION_ROLES
from app.core.security import generate_urlsafe_token, hash_password, hash_token, verify_password
from app.db.session import transaction
from app.models.donor import Donor
from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.donor_repository import DonorRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RegisterRequest, TokenResponse
from app.services.audit_service import AuditService
from app.utils.date_utils import utcnow
from app.utils.enums import DonorType, Role

logger = logging.getLogger("app.email")
TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "emails"

GENERIC_RESET_MESSAGE = "If an account with that email exists, a password reset link has been sent."


def render_email(template: str, **context) -> str:
    html = (TEMPLATE_DIR / template).read_text(encoding="utf-8")
    for key, value in context.items():
        html = html.replace("{{ %s }}" % key, str(value))
    return html


def send_email(to: str, subject: str, html: str) -> None:
    """Email transport stub: logs the message. Plug SMTP / a provider here for real delivery."""
    logger.info("EMAIL to=%s subject=%r (%d bytes)", to, subject, len(html))


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.tokens = RefreshTokenRepository(db)
        self.donors = DonorRepository(db)
        self.audit = AuditService(db)

    # ------------------------------------------------------------------ registration
    def register(self, data: RegisterRequest) -> User:
        if data.role not in SELF_REGISTRATION_ROLES:
            raise ForbiddenError("Self-registration is limited to the volunteer and donor roles")
        email = data.email.lower()
        if self.users.get_by_email(email):
            raise ConflictError("An account with this email already exists")
        with transaction(self.db):
            user = self.users.add(
                User(email=email, full_name=data.full_name.strip(), hashed_password=hash_password(data.password), role=data.role, is_active=True)
            )
            if data.role == Role.DONOR:
                donor = self.donors.get_by_email(email)
                if donor and donor.user_id is None:
                    donor.user_id = user.id  # link the pre-existing donor record created by staff
                elif not donor:
                    self.donors.add(Donor(user_id=user.id, name=user.full_name, email=email, donor_type=DonorType.INDIVIDUAL))
            self.audit.log(user, "user.registered", "user", user.id, {"email": email, "role": data.role.value})
        return user

    # ------------------------------------------------------------------ login / tokens
    def _issue_tokens(self, user: User) -> TokenResponse:
        access = create_access_token(user.id, user.role.value)
        refresh, jti, expires = create_refresh_token(user.id)
        self.tokens.add(RefreshToken(user_id=user.id, jti=jti, expires_at=expires))
        return TokenResponse(access_token=access, refresh_token=refresh, expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)

    def login(self, email: str, password: str) -> TokenResponse:
        user = self.users.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password")
        if not user.is_active:
            raise ForbiddenError("Account is deactivated. Contact an administrator.")
        with transaction(self.db):
            result = self._issue_tokens(user)
            self.audit.log(user, "auth.login", "user", user.id)
        return result

    def refresh(self, refresh_token: str) -> TokenResponse:
        payload = decode_token(refresh_token, REFRESH)
        record = self.tokens.get_by_jti(payload["jti"])
        if not record or record.revoked or record.expires_at < utcnow():
            raise UnauthorizedError("Refresh token is invalid or has been revoked")
        user = self.users.get(record.user_id)
        if not user or not user.is_active:
            raise UnauthorizedError("Account is unavailable")
        with transaction(self.db):
            record.revoked = True  # rotation: every refresh token is single-use
            return self._issue_tokens(user)

    def logout(self, refresh_token: str) -> None:
        payload = decode_token(refresh_token, REFRESH)
        with transaction(self.db):
            record = self.tokens.get_by_jti(payload["jti"])
            if record:
                record.revoked = True

    # ------------------------------------------------------------------ password flows
    def forgot_password(self, email: str) -> tuple[str, str | None]:
        """Always returns the same message so account existence is not leaked."""
        user = self.users.get_by_email(email)
        if not user or not user.is_active:
            return GENERIC_RESET_MESSAGE, None
        raw = generate_urlsafe_token()
        with transaction(self.db):
            self.tokens.invalidate_reset_tokens(user.id)
            self.tokens.add_reset_token(
                PasswordResetToken(
                    user_id=user.id, token_hash=hash_token(raw),
                    expires_at=utcnow() + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES),
                )
            )
            self.audit.log(user, "auth.password_reset_requested", "user", user.id)
        html = render_email(
            "password_reset.html", name=user.full_name, token=raw, expires_minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES
        )
        send_email(user.email, "Reset your password", html)
        return GENERIC_RESET_MESSAGE, (raw if settings.EXPOSE_RESET_TOKEN else None)

    def reset_password(self, token: str, new_password: str) -> None:
        record = self.tokens.get_reset_token(hash_token(token))
        if not record or record.used or record.expires_at < utcnow():
            raise UnauthorizedError("Reset token is invalid or has expired")
        user = self.users.get(record.user_id)
        if not user or not user.is_active:
            raise UnauthorizedError("Reset token is invalid or has expired")
        with transaction(self.db):
            user.hashed_password = hash_password(new_password)
            record.used = True
            self.tokens.revoke_all_for_user(user.id)  # force re-login everywhere
            self.audit.log(user, "auth.password_reset", "user", user.id)

    def change_password(self, user: User, current: str, new: str) -> None:
        if not verify_password(current, user.hashed_password):
            raise UnauthorizedError("Current password is incorrect")
        with transaction(self.db):
            user.hashed_password = hash_password(new)
            self.tokens.revoke_all_for_user(user.id)
            self.audit.log(user, "auth.password_changed", "user", user.id)
