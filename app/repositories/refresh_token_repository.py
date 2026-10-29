from sqlalchemy import select, update

from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.repositories import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    def get_by_jti(self, jti: str) -> RefreshToken | None:
        return self.db.scalar(select(RefreshToken).where(RefreshToken.jti == jti))

    def revoke_all_for_user(self, user_id: int) -> None:
        self.db.execute(update(RefreshToken).where(RefreshToken.user_id == user_id).values(revoked=True))

    # --- password reset tokens live here too: they are the same kind of credential record ---
    def add_reset_token(self, token: PasswordResetToken) -> PasswordResetToken:
        self.db.add(token)
        self.db.flush()
        return token

    def get_reset_token(self, token_hash: str) -> PasswordResetToken | None:
        return self.db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash))

    def invalidate_reset_tokens(self, user_id: int) -> None:
        self.db.execute(
            update(PasswordResetToken).where(PasswordResetToken.user_id == user_id, PasswordResetToken.used.is_(False)).values(used=True)
        )
