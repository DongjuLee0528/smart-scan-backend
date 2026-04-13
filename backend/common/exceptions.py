"""
커스텀 예외 처리 모듈

SmartScan 백엔드 애플리케이션의 예외 처리를 위한 커스텀 예외 클래스들과
글로벌 예외 핸들러를 정의합니다. 일관된 에러 응답 형식을 보장합니다.

제공하는 예외 클래스:
- CustomException: 기본 커스텀 예외 클래스
- NotFoundException: 404 리소스 없음 예외
- BadRequestException: 400 잘못된 요청 예외
- ConflictException: 409 충돌 예외
- UnauthorizedException: 401 인증 실패 예외

모든 예외는 통일된 JSON 응답 형식으로 변환됩니다.
"""

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from backend.common.response import error_response


class CustomException(Exception):
    def __init__(self, status_code: int, message: str, detail: str = None):
        self.status_code = status_code
        self.message = message
        self.detail = detail


class NotFoundException(CustomException):
    def __init__(self, message: str = "Resource not found", detail: str = None):
        super().__init__(404, message, detail)


class BadRequestException(CustomException):
    def __init__(self, message: str = "Validation failed", detail: str = None):
        super().__init__(400, message, detail)


class ForbiddenException(CustomException):
    def __init__(self, message: str = "Forbidden", detail: str = None):
        super().__init__(403, message, detail)


class UnauthorizedException(CustomException):
    def __init__(self, message: str = "Unauthorized", detail: str = None):
        super().__init__(401, message, detail)


class DatabaseException(CustomException):
    def __init__(self, message: str = "Database error", detail: str = None):
        super().__init__(500, message, detail)


class ConflictException(CustomException):
    def __init__(self, message: str = "Resource already exists", detail: str = None):
        super().__init__(409, message, detail)


async def custom_exception_handler(request: Request, exc: CustomException):
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(exc.message, exc.detail)
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(exc.detail if exc.detail else "HTTP error")
    )


async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=error_response("Internal server error")
    )
