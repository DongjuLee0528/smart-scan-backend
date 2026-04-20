"""
챗봇 서비스-투-서비스 인증 의존성

/api/chatbot/* 엔드포인트는 카카오 OpenBuilder 웹훅을 받는
smartscan-chatbot Lambda만 호출해야 한다. X-Chatbot-Key 헤더로 공유 비밀키를 검증한다.

JWT_SECRET_KEY / KAKAO_LINK_JWT_SECRET 와 격리된 별도 시크릿을 사용하여
한쪽이 유출되어도 다른 경로의 보안이 영향을 받지 않도록 한다.
"""

import hmac

from fastapi import Header

from backend.common.config import settings
from backend.common.exceptions import UnauthorizedException


def require_chatbot_key(x_chatbot_key: str | None = Header(default=None, alias="X-Chatbot-Key")) -> None:
    """X-Chatbot-Key 헤더 검증. 누락 또는 불일치 시 401."""
    if not x_chatbot_key:
        raise UnauthorizedException("X-Chatbot-Key header is required")
    if not hmac.compare_digest(x_chatbot_key.strip(), settings.CHATBOT_SHARED_KEY):
        raise UnauthorizedException("Invalid X-Chatbot-Key")
