from datetime import datetime, timezone


def normalize_datetime(value: datetime | None) -> datetime | None:
    """
    Normalize datetime to UTC timezone.
    If the datetime is timezone-naive, assumes UTC.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def normalize_datetime_required(value: datetime) -> datetime:
    """
    Normalize datetime to UTC timezone.
    If the datetime is timezone-naive, assumes UTC.
    Raises error if value is None.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value