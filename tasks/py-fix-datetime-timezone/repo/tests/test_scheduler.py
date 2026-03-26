from datetime import datetime, timezone, timedelta
from scheduler import is_overdue, hours_until


def test_is_overdue_past():
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    assert is_overdue(past) is True


def test_is_overdue_future():
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    assert is_overdue(future) is False


def test_is_overdue_utc():
    """Deadline with UTC timezone must not raise TypeError."""
    deadline = datetime(2020, 1, 1, tzinfo=timezone.utc)
    result = is_overdue(deadline)
    assert result is True


def test_hours_until():
    future = datetime.now(timezone.utc) + timedelta(hours=2)
    assert 1.9 < hours_until(future) < 2.1
