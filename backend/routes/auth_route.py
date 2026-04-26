"""
인증 및 계정 관리 API 라우터

이 모듈은 SmartScan 시스템의 사용자 인증 관련 API 엔드포인트를 정의합니다.
회원가입, 로그인, 로그아웃, 토큰 갱신, 이메일 인증 등의 기능을 제공합니다.

주요 엔드포인트:
- POST /send-verification-email: 이메일 인증 코드 발송
- POST /verify-email: 이메일 인증 처리
- POST /register: 회원가입
- POST /login: 로그인 및 JWT 토큰 발급
- POST /logout: 로그아웃 및 토큰 무효화
- POST /refresh: 액세스 토큰 갱신

보안: Rate limiting과 JWT 토큰 기반 인증 적용
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
    이메일 인증 코드 발송

    회원가입 시 이메일 주소 확인을 위한 6자리 인증 코드를 발송합니다.
    Rate limiting이 적용되어 스팸 방지를 위해 요청 제한이 있습니다.

    Args:
        request: slowapi가 rate limit 키(IP)를 뽑기 위한 starlette Request
        payload: 이메일 주소가 포함된 요청 본문

    Returns:
        성공 시 인증 코드 발송 완료 메시지

    Raises:
        ValidationError: 이메일 형식이 잘못된 경우
        RateLimitExceeded: 요청 제한 초과 시
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
    이메일 인증 코드 검증

    발송된 6자리 인증 코드를 검증하여 이메일 주소 소유권을 확인합니다.
    인증 완료 시 회원가입 절차를 계속 진행할 수 있습니다.

    Args:
        request: slowapi가 rate limit 키(IP)를 뽑기 위한 starlette Request
        payload: 이메일 주소와 인증 코드가 포함된 요청 본문

    Returns:
        성공 시 이메일 인증 완료 메시지

    Raises:
        ValidationError: 인증 코드가 잘못되었거나 만료된 경우
        RateLimitExceeded: 요청 제한 초과 시
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
    회원가입

    이메일 인증을 완료한 후 카카오 연동 회원가입을 진행합니다.
    회원가입과 동시에 개인 가족을 생성하고 소유자로 등록됩니다.

    Args:
        request: slowapi가 rate limit 키(IP)를 뽑기 위한 starlette Request
        payload: 회원가입 정보 (카카오 ID, 이름, 이메일, 비밀번호 등)

    Returns:
        성공 시 생성된 사용자 및 가족 정보

    Raises:
        ValidationError: 필수 정보 누락 또는 형식 오류
        ConflictError: 이미 등록된 이메일 또는 카카오 ID
        RateLimitExceeded: 요청 제한 초과 시
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
    카카오 계정 연동 (magic link)

    챗봇 Lambda가 발급한 단기 JWT를 검증하여 현재 로그인 사용자의
    kakao_user_id를 실제 카카오 UID로 교체한다.
    """
    result = auth_service.link_kakao(current_user.id, payload.token)
    return success_response(
        "Kakao account linked successfully",
        result.model_dump()
    )