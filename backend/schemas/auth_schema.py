"""
인증 관련 API 스키마

Smart Scan 시스템의 사용자 인증 플로우를 위한 API 요청/응답 스키마를 정의합니다.
이메일 인증, 회원가입, 로그인, JWT 토큰 관리 등의 모든 인증 과정을 지원합니다.

주요 스키마:
- SendVerificationEmailRequest/Response: 이메일 인증 코드 발송
- VerifyEmailRequest/Response: 이메일 인증 코드 검증
- RegisterRequest/Response: 카카오 연동 회원가입
- LoginRequest: 이메일/비밀번호 로그인
- AuthTokenResponse: JWT 토큰 쌍 (access + refresh)
- LogoutRequest/Response: 로그아웃

데이터 검증:
- 이메일 형식 및 중복 검사
- 6자리 숫자 인증 코드 검증
- 카카오 사용자 ID 연동
- 비밀번호 강도 검증 (공통 유틸리티에서 처리)

비즈니스 규칙:
- 이메일 인증 필수 회원가입 정책
- 카카오 ID와 이메일 연동 지원
- JWT 기반 인증 (access token + refresh token)
- Refresh token rotation을 통한 보안 강화
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class SendVerificationEmailRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        value = v.strip()
        if not value:
            raise ValueError("email is required")
        return value


class VerifyEmailRequest(BaseModel):
    email: str
    code: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        value = v.strip()
        if not value:
            raise ValueError("email is required")
        return value

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        value = v.strip()
        if not value:
            raise ValueError("code is required")
        if not value.isdigit() or len(value) != 6:
            raise ValueError("code must be 6 digits")
        return value


class RegisterRequest(BaseModel):
    kakao_user_id: str
    name: str
    email: str
    password: str
    phone: Optional[str] = None
    age: Optional[int] = None
    family_name: Optional[str] = None

    @field_validator("kakao_user_id", "name", "email", "password")
    @classmethod
    def validate_required_text(cls, v: str, info) -> str:
        value = v.strip()
        if not value:
            raise ValueError(f"{info.field_name} is required")
        return value

    @field_validator("phone", "family_name")
    @classmethod
    def normalize_optional_text(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None

        value = v.strip()
        return value or None


class SendVerificationEmailResponse(BaseModel):
    email: str
    expires_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VerifyEmailResponse(BaseModel):
    email: str
    verified_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RegisterResponse(BaseModel):
    user_id: int
    kakao_user_id: str
    email: str
    name: str
    family_id: int
    family_name: str
    family_member_id: int
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email", "password")
    @classmethod
    def validate_required_text(cls, v: str, info) -> str:
        value = v.strip()
        if not value:
            raise ValueError(f"{info.field_name} is required")
        return value


class RefreshRequest(BaseModel):
    refresh_token: str

    @field_validator("refresh_token")
    @classmethod
    def validate_refresh_token(cls, v: str) -> str:
        value = v.strip()
        if not value:
            raise ValueError("refresh_token is required")
        return value


class LogoutRequest(BaseModel):
    refresh_token: str

    @field_validator("refresh_token")
    @classmethod
    def validate_refresh_token(cls, v: str) -> str:
        value = v.strip()
        if not value:
            raise ValueError("refresh_token is required")
        return value


class AuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime
    user_id: int
    kakao_user_id: str
    email: Optional[str] = None
    name: Optional[str] = None


class LogoutResponse(BaseModel):
    logged_out: bool
