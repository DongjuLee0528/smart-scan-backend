from functools import wraps

from fastapi import HTTPException
from pydantic import ValidationError

from backend.common.exceptions import BadRequestException


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
            # 개발 시 디버깅을 위해 원본 에러 메시지 포함
            error_detail = f"서버 오류가 발생했습니다: {str(e)}" if str(e) else "서버 오류가 발생했습니다"
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