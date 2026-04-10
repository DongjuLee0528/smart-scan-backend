import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt

from backend.common.config import settings
from backend.common.exceptions import UnauthorizedException


def hash_password(password: str) -> str:
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
    return encode_jwt(payload), expires_at


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
    return encode_jwt(payload), expires_at


def encode_jwt(payload: dict) -> str:
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, expected_type: str | None = None) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedException("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedException("Invalid token") from exc

    if expected_type and payload.get("type") != expected_type:
        raise UnauthorizedException("Invalid token type")

    return payload
