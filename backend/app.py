from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.common.config import settings
from backend.common.exceptions import (
    CustomException,
    custom_exception_handler,
    http_exception_handler,
    general_exception_handler
)


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
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 예외 핸들러 등록
    app.add_exception_handler(CustomException, custom_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    from backend.routes import device_route, item_route, label_route, scan_log_route

    app.include_router(device_route.router, prefix="/api/devices")
    app.include_router(item_route.router, prefix="/api/items")
    app.include_router(label_route.router, prefix="/api/labels")
    app.include_router(scan_log_route.router, prefix="/api/scan-logs")

    @app.get("/")
    async def root():
        return {"message": "Smart Scan API is running"}

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    return app


app = create_app()
