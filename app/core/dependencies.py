from typing import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.jwt import ACCESS, decode_token
from app.core.permissions import Permission, has_permission
from app.db.session import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False, description="JWT access token")


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme), db: Session = Depends(get_db)
) -> User:
    if creds is None:
        raise UnauthorizedError("Not authenticated")
    payload = decode_token(creds.credentials, ACCESS)
    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise UnauthorizedError("User no longer exists")
    if not user.is_active:
        raise ForbiddenError("Account is deactivated")
    return user


def require_permissions(*permissions: Permission, any_of: bool = True) -> Callable[..., User]:
    """Dependency factory. By default the user needs ANY of the listed permissions."""

    def checker(user: User = Depends(get_current_user)) -> User:
        checks = [has_permission(user.role, p) for p in permissions]
        ok = any(checks) if any_of else all(checks)
        if not ok:
            raise ForbiddenError("You do not have permission to perform this action")
        return user

    return checker
