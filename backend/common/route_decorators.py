"""
API route decorator module

Provides common decorators that can be applied to FastAPI route functions.
Automates exception handling, input validation, security processing to prevent code duplication.

Provided decorators:
- @handle_service_errors: Automatic service layer exception handling
- validate_required_string(): Required string validation
- Sensitive information exposure prevention features

Security features:
- Remove sensitive information like passwords, tokens from error messages
- Adjust error detail level by development/production environment
"""

import asyncio
import re
from functools import wraps

from fastapi import HTTPException
from pydantic import ValidationError

from backend.common.exceptions import BadRequestException, CustomException
from backend.common.config import settings


def _sanitize_error_message(error_msg: str) -> str:
    """Return error message with sensitive information removed even in development environment"""
    if not error_msg:
        return "Server error occurred"

    # Remove lines containing passwords, tokens, keys, etc.
    # Regex patterns to match common sensitive data formats
    sensitive_patterns = [
        r'password[=\s:][^\s]+',
        r'token[=\s:][^\s]+',
        r'key[=\s:][^\s]+',
        r'secret[=\s:][^\s]+',
        r'auth[=\s:][^\s]+',
        r'/[a-zA-Z0-9/_-]*password[a-zA-Z0-9/_-]*',
        r'/[a-zA-Z0-9/_-]*secret[a-zA-Z0-9/_-]*',
        r'postgresql://[^/]+',  # Database connection strings
        r'mysql://[^/]+',
    ]

    sanitized = error_msg
    # Apply each pattern to redact sensitive information
    for pattern in sensitive_patterns:
        sanitized = re.sub(pattern, '[REDACTED]', sanitized, flags=re.IGNORECASE)

    # Truncate to first line to avoid exposing stack trace details
    lines = sanitized.split('\n')
    if len(lines) > 1:
        sanitized = lines[0]

    # Limit message length to prevent response bloat
    return f"Server error occurred: {sanitized[:200]}"


def _map_exception(e: Exception) -> HTTPException:
    """Common exception mapping logic. BadRequest/HTTPException should be re-propagated
    as-is using isinstance check in caller."""
    # Provide different error detail levels based on environment
    if settings.ENV == "development":
        # Show sanitized error details in development for debugging
        error_detail = _sanitize_error_message(str(e))
    else:
        # Hide all error details in production for security
        error_detail = "Server error occurred"
    return HTTPException(status_code=500, detail=error_detail)


def handle_service_errors(func):
    """Decorator to handle common service errors in routes.

    Automatically wraps route functions with exception handling.
    Chooses async or sync wrapper based on function type for proper FastAPI compatibility.
    """
    # Check if function is async to choose appropriate wrapper pattern
    if asyncio.iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except ValidationError as e:
                # Convert Pydantic validation errors to user-friendly format
                raise BadRequestException(f"Input validation failed: {str(e)}")
            except Exception as e:
                if isinstance(e, (CustomException, HTTPException)):
                    raise
                raise _map_exception(e)
        return async_wrapper

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            raise BadRequestException(f"Input validation failed: {str(e)}")
        except Exception as e:
            # CustomException (Unauthorized/NotFound/Conflict/Forbidden/Database/BadRequest)
            # and HTTPException are delegated to global exception handler to maintain
            # proper status codes and messages.
            if isinstance(e, (CustomException, HTTPException)):
                raise
            raise _map_exception(e)
    return sync_wrapper


def validate_positive_id(param_name: str, value: int) -> None:
    """Validate that an ID parameter is positive"""
    if value <= 0:
        raise BadRequestException(f"{param_name} must be a positive number")


def validate_required_string(param_name: str, value: str | None) -> None:
    """Validate that a string parameter is not empty"""
    if not value or not value.strip():
        raise BadRequestException(f"{param_name} is required")