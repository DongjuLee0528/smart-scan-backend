from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from backend.common.response import error_response


class CustomException(Exception):
    def __init__(self, status_code: int, message: str, detail: str = None):
        self.status_code = status_code
        self.message = message
        self.detail = detail


class NotFoundError(CustomException):
    def __init__(self, message: str = "Resource not found", detail: str = None):
        super().__init__(404, message, detail)


class ValidationError(CustomException):
    def __init__(self, message: str = "Validation failed", detail: str = None):
        super().__init__(400, message, detail)


class DatabaseError(CustomException):
    def __init__(self, message: str = "Database error", detail: str = None):
        super().__init__(500, message, detail)


class DuplicateError(CustomException):
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