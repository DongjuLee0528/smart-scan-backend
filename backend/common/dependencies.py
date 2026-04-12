"""
FastAPI 의존성 주입 모듈

API 엔드포인트에서 공통적으로 사용되는 의존성들을 정의한다.
주로 JWT 토큰 기반 사용자 인증과 인가 처리를 담당한다.

주요 의존성:
- get_current_user: JWT 토큰으로부터 현재 로그인된 사용자 정보 추출
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
    JWT 토큰으로부터 현재 인증된 사용자 정보 추출

    Authorization 헤더의 Bearer 토큰을 검증하여 현재 로그인한 사용자를 반환한다.
    API 엔드포인트에서 인증이 필요한 경우 이 의존성을 사용한다.

    Args:
        credentials: HTTP Authorization 헤더에서 추출된 Bearer 토큰
        db: 데이터베이스 세션

    Returns:
        User: 인증된 사용자 객체

    Raises:
        UnauthorizedException: 토큰이 없거나 유효하지 않은 경우
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
