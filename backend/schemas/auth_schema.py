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
