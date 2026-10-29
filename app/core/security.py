import hashlib
import re
import secrets

import bcrypt

PASSWORD_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,128}$")


def validate_password_strength(password: str) -> str:
    if not PASSWORD_RE.match(password):
        raise ValueError("Password must be 8-128 characters and contain at least one letter and one digit")
    return password


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except ValueError:
        return False


def generate_urlsafe_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    """One-way hash used to store reset / refresh tokens at rest."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
