"""
SmartScan Backend Application Entry Point

이 모듈은 SmartScan 시스템의 FastAPI 백엔드 애플리케이션을 구성하고 초기화합니다.
UHF RFID 기반 소지품 체크 시스템의 웹 API 서버 역할을 담당합니다.

주요 기능:
- CORS 미들웨어 설정으로 프론트엔드와의 통신 허용
- Rate limiting으로 API 보안 강화
- 전역 예외 처리기 설정
- 모든 라우터 등록 및 API 엔드포인트 구성

배포: Render 클라우드 플랫폼에 배포되며, 환경변수를 통해 설정 관리
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from backend.common.config import settings
from backend.common.exceptions import (
    CustomException,
    custom_exception_handler,
    http_exception_handler,
    general_exception_handler
)
from backend.common.rate_limiter import limiter, rate_limit_exceeded_handler


def create_app() -> FastAPI:
    app = FastAPI(
        title="Smart Scan API",
        description="Smart Scan Backend API",
        version="1.0.0",
        docs_url="/docs" if settings.ENV == "development" else None,
        redoc_url="/redoc" if settings.ENV == "development" else None
    )

    # CORS 설정
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.ALLOWED_ORIGIN],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )

    # Rate limiter 설정
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    # 예외 핸들러 등록
    app.add_exception_handler(CustomException, custom_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    from backend.routes import (
        auth_route,
        device_route,
        family_member_route,
        item_route,
        label_route,
        monitoring_route,
        notification_route,
        scan_log_route,
        tag_route,
    )

    app.include_router(auth_route.router, prefix="/api/auth")
    app.include_router(device_route.router, prefix="/api/devices")
    app.include_router(family_member_route.router, prefix="/api/families/members")
    app.include_router(item_route.router, prefix="/api/items")
    app.include_router(label_route.router, prefix="/api/labels")
    # Monitoring routes are registered separately from tag CRUD routes.
    app.include_router(monitoring_route.router, prefix="/api/monitoring")
    app.include_router(notification_route.router, prefix="/api/notifications")
    app.include_router(scan_log_route.router, prefix="/api/scan-logs")
    app.include_router(tag_route.router, prefix="/api/tags")

    @app.get("/")
    async def root():
        return {"message": "Smart Scan API is running"}

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    return app


app = create_app()
