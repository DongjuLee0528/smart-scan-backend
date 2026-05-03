"""
FastAPI dependency injection module

Defines dependencies commonly used in API endpoints.
Primarily handles JWT token-based user authentication and authorization.

Main dependencies:
- get_current_user: Extract current logged-in user information from JWT token
"""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.common.db import get_db
from backend.common.exceptions import UnauthorizedException
from backend.common.security import decode_token
from backend.repositories.user_repository import UserRepository


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db)
):
    """
    Extract current authenticated user information from JWT token

    Validates the Bearer token in the Authorization header and returns the currently logged-in user.
    Use this dependency when authentication is required in API endpoints.

    Args:
        credentials: Bearer token extracted from HTTP Authorization header
        db: Database session

    Returns:
        User: Authenticated user object

    Raises:
        UnauthorizedException: When token is missing or invalid
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedException("Authorization header is required")

    payload = decode_token(credentials.credentials, expected_type="access")
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Invalid access token payload")

    user = UserRepository(db).find_by_id(int(user_id))
    if not user:
        raise UnauthorizedException("User not found")

    return user
