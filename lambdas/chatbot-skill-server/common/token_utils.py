"""
카카오 계정 연동용 magic link JWT 유틸리티

웹 백엔드의 security.py:create_kakao_link_token 과 동일한 페이로드/시크릿을 사용한다.
Lambda 환경변수 KAKAO_LINK_JWT_SECRET 은 웹 백엔드의 값과 반드시 동일해야 한다.
"""
import os
from datetime import datetime, timedelta, timezone

import jwt


def create_kakao_link_token(kakao_user_id: str) -> str:
    """
    카카오 사용자 ID를 payload에 담은 단기 JWT를 생성한다.

    웹 /link-kakao?token=<JWT> 링크에 포함되어 전달된다.
    웹 백엔드가 KAKAO_LINK_JWT_SECRET 으로 서명을 검증하므로
    양쪽 시크릿이 일치해야 한다.

    환경변수:
        KAKAO_LINK_JWT_SECRET         (필수) - 32자 이상 비밀키
        KAKAO_LINK_TOKEN_EXPIRE_MINUTES (선택, 기본 5)
    """
    secret = os.environ["KAKAO_LINK_JWT_SECRET"]
    expire_minutes = int(os.environ.get("KAKAO_LINK_TOKEN_EXPIRE_MINUTES", "5"))

    now = datetime.now(timezone.utc)
    payload = {
        "kakao_user_id": kakao_user_id.strip(),
        "type": "kakao_link",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expire_minutes)).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm="HS256")
