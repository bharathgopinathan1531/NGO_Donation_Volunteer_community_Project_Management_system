import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedError

ACCESS = "access"
REFRESH = "refresh"


def _encode(subject: str, token_type: str, expires: timedelta, extra: dict | None = None) -> tuple[str, str, datetime]:
    now = datetime.now(timezone.utc)
    expire = now + expires
    jti = uuid.uuid4().hex
    payload = {"sub": subject, "type": token_type, "jti": jti, "iat": now, "exp": expire, **(extra or {})}
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti, expire.replace(tzinfo=None)


def create_access_token(user_id: int, role: str) -> str:
    token, _, _ = _encode(
        str(user_id), ACCESS, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), {"role": role}
    )
    return token


def create_refresh_token(user_id: int) -> tuple[str, str, datetime]:
    """Returns (token, jti, expires_at_naive_utc)."""
    return _encode(str(user_id), REFRESH, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))


def decode_token(token: str, expected_type: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Token has expired")
    except jwt.PyJWTError:
        raise UnauthorizedError("Invalid token")
    if payload.get("type") != expected_type:
        raise UnauthorizedError("Invalid token type")
    return payload
