from datetime import datetime, timezone, timedelta


def is_overdue(deadline: datetime) -> bool:
    """Return True if the deadline has passed."""
    return datetime.now() > deadline


def hours_until(deadline: datetime) -> float:
    """Return hours remaining until deadline (negative if overdue)."""
    now = datetime.now(timezone.utc)
    delta = deadline - now
    return delta.total_seconds() / 3600
