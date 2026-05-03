"""
SmartScan Backend Application Entry Point

This module configures and initializes the FastAPI backend application for the SmartScan system.
It serves as the web API server for a UHF RFID-based belongings check system.

Main features:
- CORS middleware setup to allow communication with frontend
- API security enhancement through rate limiting
- Global exception handler configuration
- Registration of all routers and API endpoint configuration

Deployment: Deployed on Render cloud platform with configuration management via environment variables
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

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.ALLOWED_ORIGIN],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )

    # Rate limiter configuration
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    # Register exception handlers
    app.add_exception_handler(CustomException, custom_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    from backend.routes import (
        auth_route,
        chatbot_route,
        device_route,
        family_invitation_route,
        family_member_route,
        item_route,
        label_route,
        monitoring_route,
        notification_route,
        scan_log_route,
        tag_route,
    )

    app.include_router(auth_route.router, prefix="/api/auth")
    app.include_router(chatbot_route.router, prefix="/api/chatbot")
    app.include_router(device_route.router, prefix="/api/devices")
    app.include_router(family_invitation_route.router, prefix="/api/family-invitations")
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
