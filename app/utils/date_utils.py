from datetime import date, datetime, timezone


def utcnow() -> datetime:
    """Naive UTC timestamp (all DB datetimes are naive UTC)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def today() -> date:
    return utcnow().date()


def ranges_overlap(start_a: date, end_a: date | None, start_b: date, end_b: date | None) -> bool:
    """Inclusive overlap test; a missing end date means open-ended."""
    far_future = date.max
    return start_a <= (end_b or far_future) and start_b <= (end_a or far_future)
