"""
Chatbot service-to-service authentication dependency

/api/chatbot/* endpoints should only be called by
smartscan-chatbot Lambda that receives Kakao OpenBuilder webhooks. Validates shared secret key via X-Chatbot-Key header.

Uses a separate secret isolated from JWT_SECRET_KEY / KAKAO_LINK_JWT_SECRET
so that if one side is compromised, security of other paths is not affected.
"""

import hmac

from fastapi import Header

from backend.common.config import settings
from backend.common.exceptions import UnauthorizedException


def require_chatbot_key(x_chatbot_key: str | None = Header(default=None, alias="X-Chatbot-Key")) -> None:
    """Validate X-Chatbot-Key header. Returns 401 if missing or mismatched."""
    if not x_chatbot_key:
        raise UnauthorizedException("X-Chatbot-Key header is required")
    if not hmac.compare_digest(x_chatbot_key.strip(), settings.CHATBOT_SHARED_KEY):
        raise UnauthorizedException("Invalid X-Chatbot-Key")
