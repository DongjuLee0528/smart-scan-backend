"""
Datetime utility functions

Provides common utility functions for datetime processing used in the SmartScan system.
Normalizes all datetime to UTC to ensure timezone consistency between database and API.

Main features:
- Convert naive datetime without timezone info to UTC
- UTC conversion of aware datetime with timezone info
- Separate handling for optional and required datetime

Usage purposes:
- Normalize JWT token expiration time
- Normalize datetime before database storage
- Provide consistent timezone in API responses
- Validate email verification expiration time

Timezone policy:
- All system internal processing is based on UTC
- Apply local timezone only for client display
- Force UTC application when storing in database
"""

from datetime import datetime, timezone


def normalize_datetime(value: datetime | None) -> datetime | None:
    """
    Normalize optional datetime to UTC timezone

    Converts naive datetime without timezone info to UTC.
    Returns None value as-is to support optional field handling.

    Args:
        value: datetime object to normalize or None

    Returns:
        datetime | None: datetime with UTC timezone set or None

    Usage example:
        Normalizing optional timestamp fields in API responses
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def normalize_datetime_required(value: datetime) -> datetime:
    """
    Normalize required datetime to UTC timezone

    Converts naive datetime without timezone info to UTC.
    Type error occurs if None value is passed, so should only be used for required fields.

    Args:
        value: datetime object to normalize (required)

    Returns:
        datetime: datetime with UTC timezone set

    Raises:
        AttributeError: when value is None

    Usage example:
        Normalizing JWT token expiration time, database storage time
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value