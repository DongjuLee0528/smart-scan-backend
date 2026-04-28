"""
Security-related utility module

Module responsible for authentication, password hashing, JWT token management and other security features of SmartScan system.
Implements PBKDF2-based password hashing and JWT access/refresh token system.

Security features:
- Secure password hashing using PBKDF2 + Salt
- JWT access token (15-minute expiry) and refresh token (30-day expiry) issuance
- Token validation and payload extraction
- HMAC-based secure hash generation

Security policies:
- Password: PBKDF2-HMAC-SHA256, 100,000 iterations, 16-byte salt
- JWT: HS256 algorithm, dynamic expiration time settings
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from jwt import InvalidTokenError

from backend.common.config import settings
from backend.common.exceptions import UnauthorizedException


def hash_password(password: str) -> str:
    """
    Password hashing (PBKDF2-HMAC-SHA256)

    Generates hash using PBKDF2 algorithm and random salt for secure password storage.
    Strengthens security against rainbow table attacks and brute force attacks.

    Args:
        password: Plain text password

    Returns:
        Formatted hash string (pbkdf2_sha256$iterations$salt$hash)

    Security:
        - Uses PBKDF2-HMAC-SHA256 algorithm
        - 100,000 iterations (settings.PASSWORD_HASH_ITERATIONS)
        - 16-byte random salt generation
    """
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        settings.PASSWORD_HASH_ITERATIONS
    )
    return (
        f"pbkdf2_sha256${settings.PASSWORD_HASH_ITERATIONS}$"
        f"{salt.hex()}${digest.hex()}"
    )


def verify_password(password: str, password_hash: str | None) -> bool:
    """
    Password verification

    Compares user-entered plain password with stored hash to check if they match.
    Uses hmac.compare_digest to prevent timing attacks.

    Args:
        password: User-entered plain password
        password_hash: Hash stored in database (None allowed)

    Returns:
        Password match status (bool)

    Security:
        - Prevents timing attacks with hmac.compare_digest
        - Returns False for invalid format hash
        - Safely handles None hash as False
    """
    if not password_hash:
        return False

    try:
        algorithm, iterations, salt_hex, digest_hex = password_hash.split("$", 3)
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    calculated_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        int(iterations)
    ).hex()
    return hmac.compare_digest(calculated_digest, digest_hex)


def generate_token_id() -> str:
    return uuid4().hex


def create_access_token(user_id: int) -> tuple[str, datetime]:
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp())
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, expires_at


def create_refresh_token(user_id: int, token_id: str) -> tuple[str, datetime]:
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": token_id,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp())
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, expires_at


def decode_token(token: str, expected_type: str | None = None) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        if expected_type and payload.get("type") != expected_type:
            raise UnauthorizedException("Invalid token type")

        return payload

    except InvalidTokenError as exc:
        raise UnauthorizedException("Invalid or expired token") from exc


def create_kakao_link_token(kakao_user_id: str) -> tuple[str, datetime]:
    """
    Issue short-term JWT for Kakao account linking

    Token included in links sent to unlinked users by chatbot Lambda.
    When user submits this token while logged in on web, the kakao_user_id
    is linked to the current logged-in user's account.

    Signs with KAKAO_LINK_JWT_SECRET separate from JWT_SECRET_KEY to isolate
    token systems so that if one is compromised, the other remains secure.
    """
    if not kakao_user_id or not kakao_user_id.strip():
        raise ValueError("kakao_user_id is required")

    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(minutes=settings.KAKAO_LINK_TOKEN_EXPIRE_MINUTES)
    payload = {
        "kakao_user_id": kakao_user_id.strip(),
        "type": "kakao_link",
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(
        payload,
        settings.KAKAO_LINK_JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    return token, expires_at


def decode_kakao_link_token(token: str) -> dict:
    """
    Verify Kakao account linking JWT and return payload

    Verifies signature with KAKAO_LINK_JWT_SECRET, checks type=="kakao_link" and expiration.
    Returns payload with {"kakao_user_id", "type", "iat", "exp"} structure.
    """
    try:
        payload = jwt.decode(
            token,
            settings.KAKAO_LINK_JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except InvalidTokenError as exc:
        raise UnauthorizedException("Invalid or expired kakao link token") from exc

    if payload.get("type") != "kakao_link":
        raise UnauthorizedException("Invalid token type")

    kakao_user_id = payload.get("kakao_user_id")
    if not kakao_user_id or not isinstance(kakao_user_id, str):
        raise UnauthorizedException("Invalid kakao link token payload")

    return payload
