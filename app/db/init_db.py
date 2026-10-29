"""Database bootstrap helpers (dev convenience; production uses Alembic migrations)."""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import engine
from app.models.user import User
from app.utils.enums import Role

logger = logging.getLogger(__name__)


def create_tables() -> None:
    import app.models  # noqa: F401  (register all models)

    Base.metadata.create_all(bind=engine)


def ensure_super_admin(db: Session, email: str | None = None, password: str | None = None, name: str | None = None) -> User:
    email = (email or settings.SUPER_ADMIN_EMAIL).lower()
    user = db.scalar(select(User).where(User.email == email))
    if user:
        return user
    user = User(
        email=email,
        full_name=name or settings.SUPER_ADMIN_NAME,
        hashed_password=hash_password(password or settings.SUPER_ADMIN_PASSWORD),
        role=Role.SUPER_ADMIN,
        is_active=True,
    )
    db.add(user)
    db.commit()
    logger.info("Created super admin %s", email)
    return user
