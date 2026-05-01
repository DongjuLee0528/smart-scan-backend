from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse


# Create rate limiter instance
limiter = Limiter(key_func=get_remote_address)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Return user-friendly error message when rate limit is exceeded"""
    response = JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please try again later."}
    )
    response = _rate_limit_exceeded_handler(request, exc)
    return response


# Common rate limit settings
auth_rate_limit = "5/minute"  # Login/registration
api_rate_limit = "30/minute"  # General API