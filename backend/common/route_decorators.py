"""
API 라우트 데코레이터 모듈

FastAPI 라우트 함수에 적용할 수 있는 공통 데코레이터들을 제공합니다.
예외 처리, 입력 검증, 보안 처리 등을 자동화하여 코드 중복을 방지합니다.

제공 데코레이터:
- @handle_service_errors: 서비스 레이어 예외 자동 처리
- validate_required_string(): 필수 문자열 검증
- 민감 정보 노출 방지 기능

보안 기능:
- 에러 메시지에서 비밀번호, 토큰 등 민감 정보 제거
- 개발/운영 환경별 에러 세부 수준 조절
"""

import re
from functools import wraps

from fastapi import HTTPException
from pydantic import ValidationError

from backend.common.exceptions import BadRequestException
from backend.common.config import settings


def _sanitize_error_message(error_msg: str) -> str:
    """개발 환경에서도 민감한 정보를 제거한 에러 메시지 반환"""
    if not error_msg:
        return "서버 오류가 발생했습니다"

    # 패스워드, 토큰, 키 등이 포함된 라인 제거
    sensitive_patterns = [
        r'password[=\s:][^\s]+',
        r'token[=\s:][^\s]+',
        r'key[=\s:][^\s]+',
        r'secret[=\s:][^\s]+',
        r'auth[=\s:][^\s]+',
        r'/[a-zA-Z0-9/_-]*password[a-zA-Z0-9/_-]*',
        r'/[a-zA-Z0-9/_-]*secret[a-zA-Z0-9/_-]*',
        r'postgresql://[^/]+',
        r'mysql://[^/]+',
    ]

    sanitized = error_msg
    for pattern in sensitive_patterns:
        sanitized = re.sub(pattern, '[REDACTED]', sanitized, flags=re.IGNORECASE)

    # 긴 스택 트레이스는 첫 번째 라인만 유지
    lines = sanitized.split('\n')
    if len(lines) > 1:
        sanitized = lines[0]

    return f"서버 오류가 발생했습니다: {sanitized[:200]}"


def handle_service_errors(func):
    """Decorator to handle common service errors in routes"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            raise BadRequestException(f"입력값 검증 실패: {str(e)}")
        except Exception as e:
            if isinstance(e, (BadRequestException, HTTPException)):
                raise
            # 개발 환경에서는 sanitized 에러 메시지, 운영 환경에서는 일반 메시지만 반환
            if settings.ENV == "development":
                error_detail = _sanitize_error_message(str(e))
            else:
                error_detail = "서버 오류가 발생했습니다"
            raise HTTPException(status_code=500, detail=error_detail)
    return wrapper


def validate_positive_id(param_name: str, value: int) -> None:
    """Validate that an ID parameter is positive"""
    if value <= 0:
        raise BadRequestException(f"{param_name}는 양수여야 합니다")


def validate_required_string(param_name: str, value: str | None) -> None:
    """Validate that a string parameter is not empty"""
    if not value or not value.strip():
        raise BadRequestException(f"{param_name}은 필수입니다")