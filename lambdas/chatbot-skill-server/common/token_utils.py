"""
Magic link JWT utility for Kakao account integration

Uses the same payload/secret as web backend's security.py:create_kakao_link_token.
Lambda environment variable KAKAO_LINK_JWT_SECRET must match the web backend value.
"""
import os
from datetime import datetime, timedelta, timezone

import jwt


def create_kakao_link_token(kakao_user_id: str) -> str:
    """
    Generate short-term JWT containing Kakao user ID in payload.

    Transmitted in web /link-kakao?token=<JWT> link.
    Web backend verifies signature with KAKAO_LINK_JWT_SECRET so
    both secrets must match.

    Environment variables:
        KAKAO_LINK_JWT_SECRET         (required) - 32+ character secret key
        KAKAO_LINK_TOKEN_EXPIRE_MINUTES (optional, default 5)
    """
    secret = os.environ.get("KAKAO_LINK_JWT_SECRET")
    if not secret:
        raise ValueError("KAKAO_LINK_JWT_SECRET environment variable is not set")
    expire_minutes = int(os.environ.get("KAKAO_LINK_TOKEN_EXPIRE_MINUTES", "5"))

    now = datetime.now(timezone.utc)
    payload = {
        "kakao_user_id": kakao_user_id.strip(),
        "type": "kakao_link",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expire_minutes)).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm="HS256")
