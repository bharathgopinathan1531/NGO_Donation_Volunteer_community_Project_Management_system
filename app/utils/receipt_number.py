import secrets

from app.utils.date_utils import utcnow

_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_receipt_number() -> str:
    """e.g. RCT-20261026-7K2M9QXA. Uniqueness is guaranteed by a DB unique constraint (callers retry on conflict)."""
    suffix = "".join(secrets.choice(_ALPHABET) for _ in range(8))
    return f"RCT-{utcnow():%Y%m%d}-{suffix}"
