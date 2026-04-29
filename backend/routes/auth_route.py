"""
Authentication and account management API router

This module defines user authentication-related API endpoints for SmartScan system.
Provides registration, login, logout, token refresh, email verification, and other features.

Main endpoints:
- POST /send-verification-email: Send email verification code
- POST /verify-email: Process email verification
- POST /register: User registration
- POST /login: Login and JWT token issuance
- POST /logout: Logout and token invalidation
- POST /refresh: Access token renewal

Security: Rate limiting and JWT token-based authentication applied
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.common.dependencies import get_current_user
from backend.common.db import get_db
from backend.common.response import success_response
from backend.common.route_decorators import handle_service_errors
from backend.common.rate_limiter import limiter, auth_rate_limit, api_rate_limit
from backend.schemas.auth_schema import (
    LinkKakaoRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    SendVerificationEmailRequest,
    VerifyEmailRequest,
)
from backend.services.auth_service import AuthService


router = APIRouter(tags=["auth"])


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


@router.post("/send-verification-email")
@limiter.limit(auth_rate_limit)
@handle_service_errors
async def send_verification_email(
    request: Request,
    payload: SendVerificationEmailRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Send email verification code

    Send 6-digit verification code for email address verification during registration.
    Rate limiting is applied to prevent spam with request limits.

    Args:
        request: starlette Request for slowapi to extract rate limit key (IP)
        payload: Request body containing email address

    Returns:
        Success message for verification code sending completion

    Raises:
        ValidationError: When email format is invalid
        RateLimitExceeded: When request limit is exceeded
    """
    result = auth_service.send_verification_email(payload.email)
    return success_response(
        "Verification email sent successfully",
        result.model_dump()
    )


@router.post("/verify-email")
@limiter.limit(auth_rate_limit)
@handle_service_errors
async def verify_email(
    request: Request,
    payload: VerifyEmailRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Verify email verification code

    Verify sent 6-digit verification code to confirm email address ownership.
    Registration process can continue after verification completion.

    Args:
        request: starlette Request for slowapi to extract rate limit key (IP)
        payload: Request body containing email address and verification code

    Returns:
        Success message for email verification completion

    Raises:
        ValidationError: When verification code is invalid or expired
        RateLimitExceeded: When request limit is exceeded
    """
    result = auth_service.verify_email(payload.email, payload.code)
    return success_response(
        "Email verified successfully",
        result.model_dump()
    )


@router.post("/register")
@limiter.limit(auth_rate_limit)
@handle_service_errors
async def register(
    request: Request,
    payload: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    User registration

    Proceed with KakaoTalk-linked registration after completing email verification.
    Create personal family and register as owner simultaneously with registration.

    Args:
        request: starlette Request for slowapi to extract rate limit key (IP)
        payload: Registration information (KakaoTalk ID, name, email, password, etc.)

    Returns:
        Created user and family information on success

    Raises:
        ValidationError: Required information missing or format error
        ConflictError: Already registered email or KakaoTalk ID
        RateLimitExceeded: When request limit is exceeded
    """
    result = auth_service.register(
        kakao_user_id=payload.kakao_user_id,
        name=payload.name,
        email=payload.email,
        password=payload.password,
        phone=payload.phone,
        age=payload.age,
        family_name=payload.family_name
    )
    return success_response(
        "Registration completed successfully",
        result.model_dump()
    )


@router.post("/login")
@limiter.limit(auth_rate_limit)
@handle_service_errors
async def login(
    request: Request,
    payload: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    result = auth_service.login(payload.email, payload.password)
    return success_response(
        "Login completed successfully",
        result.model_dump()
    )


@router.post("/refresh")
@limiter.limit(auth_rate_limit)
@handle_service_errors
async def refresh(
    request: Request,
    payload: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    result = auth_service.refresh(payload.refresh_token)
    return success_response(
        "Token refreshed successfully",
        result.model_dump()
    )


@router.post("/logout")
@handle_service_errors
async def logout(
    request: LogoutRequest,
    current_user=Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    result = auth_service.logout(current_user.id, request.refresh_token)
    return success_response(
        "Logout completed successfully",
        result.model_dump()
    )


@router.post("/link-kakao")
@limiter.limit(auth_rate_limit)
@handle_service_errors
async def link_kakao(
    request: Request,
    payload: LinkKakaoRequest,
    current_user=Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Link KakaoTalk account (magic link)

    Verify short-term JWT issued by chatbot Lambda to replace
    current logged-in user's kakao_user_id with actual KakaoTalk UID.
    """
    result = auth_service.link_kakao(current_user.id, payload.token)
    return success_response(
        "Kakao account linked successfully",
        result.model_dump()
    )