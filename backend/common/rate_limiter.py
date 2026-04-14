from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse


# Rate limiter 인스턴스 생성
limiter = Limiter(key_func=get_remote_address)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Rate limit 초과 시 사용자 친화적 에러 메시지 반환"""
    response = JSONResponse(
        status_code=429,
        content={"detail": "요청이 너무 많습니다. 잠시 후 다시 시도해주세요."}
    )
    response = _rate_limit_exceeded_handler(request, exc)
    return response


# 공통 rate limit 설정
auth_rate_limit = "5/minute"  # 로그인/회원가입
api_rate_limit = "30/minute"  # 일반 API