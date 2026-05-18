"""
Rate limiting configuration for SmartScan API

Provides request rate limiting functionality to prevent abuse and ensure service stability.
Uses SlowAPI library with IP-based rate limiting for authentication and general API endpoints.

Rate limiting strategy:
- Authentication endpoints: Strict limits to prevent brute force attacks
- General API endpoints: Moderate limits for normal usage
- Per-IP tracking to identify and throttle suspicious activity
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse


# Create rate limiter instance with IP-based key function
limiter = Limiter(key_func=get_remote_address)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Custom rate limit exceeded error handler

    Returns user-friendly error message when client exceeds configured rate limits.
    Provides consistent error format across all rate-limited endpoints.
    """
    response = JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please try again later."}
    )
    response = _rate_limit_exceeded_handler(request, exc)
    return response


# Common rate limit configurations
auth_rate_limit = "5/minute"  # Authentication endpoints: strict limit for security
api_rate_limit = "30/minute"  # General API endpoints: moderate limit for normal usage