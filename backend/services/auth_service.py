import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.common.config import settings
from backend.common.datetime_utils import normalize_datetime_required
from backend.common.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
    UnauthorizedException,
)
from backend.common.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_token_id,
    hash_password,
    verify_password,
)
from backend.common.validator import (
    validate_email,
    validate_kakao_user_id,
    validate_non_empty_string,
    validate_optional_age,
    validate_password,
    validate_verification_code,
)
from backend.repositories.email_verification_repository import EmailVerificationRepository
from backend.repositories.family_member_repository import FamilyMemberRepository
from backend.repositories.family_repository import FamilyRepository
from backend.repositories.refresh_token_repository import RefreshTokenRepository
from backend.repositories.user_repository import UserRepository
from backend.schemas.auth_schema import (
    AuthTokenResponse,
    LogoutResponse,
    RegisterResponse,
    SendVerificationEmailResponse,
    VerifyEmailResponse,
)
from backend.services.email_service import EmailService


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repository = UserRepository(db)
        self.family_repository = FamilyRepository(db)
        self.family_member_repository = FamilyMemberRepository(db)
        self.email_verification_repository = EmailVerificationRepository(db)
        self.refresh_token_repository = RefreshTokenRepository(db)
        self.email_service = EmailService()

    def send_verification_email(self, email: str) -> SendVerificationEmailResponse:
        validate_email(email)
        normalized_email = email.strip()

        existing_user = self.user_repository.find_by_email(normalized_email)
        if existing_user:
            raise ConflictException("Email is already registered")

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=settings.EMAIL_VERIFICATION_EXPIRE_MINUTES)
        code = self._generate_verification_code()

        try:
            self.email_verification_repository.invalidate_pending_by_email(normalized_email, now)
            verification = self.email_verification_repository.create(normalized_email, code, expires_at)
            self.email_service.send_verification_code(normalized_email, code, expires_at)
            self.db.commit()
            self.db.refresh(verification)
            return SendVerificationEmailResponse(
                email=verification.email,
                expires_at=verification.expires_at
            )
        except Exception:
            self.db.rollback()
            raise

    def verify_email(self, email: str, code: str) -> VerifyEmailResponse:
        validate_email(email)
        validate_verification_code(code)
        normalized_email = email.strip()
        normalized_code = code.strip()

        now = datetime.now(timezone.utc)
        verification = self.email_verification_repository.find_latest_by_email_and_code(
            normalized_email,
            normalized_code
        )
        if not verification:
            raise BadRequestException("Verification code is invalid")

        if verification.used_at is not None:
            raise BadRequestException("Verification code is already used")

        if verification.expires_at <= now:
            raise BadRequestException("Verification code has expired")

        try:
            if verification.verified_at is None:
                self.email_verification_repository.mark_verified(verification, now)
                self.db.commit()
                self.db.refresh(verification)

            return VerifyEmailResponse(
                email=verification.email,
                verified_at=verification.verified_at
            )
        except Exception:
            self.db.rollback()
            raise

    def register(
        self,
        kakao_user_id: str,
        name: str,
        email: str,
        password: str,
        phone: str | None = None,
        age: int | None = None,
        family_name: str | None = None
    ) -> RegisterResponse:
        validate_kakao_user_id(kakao_user_id)
        validate_non_empty_string(name, "name")
        validate_email(email)
        validate_password(password)
        validate_optional_age(age)

        if phone is not None:
            validate_non_empty_string(phone, "phone")

        normalized_kakao_user_id = kakao_user_id.strip()
        normalized_name = name.strip()
        normalized_email = email.strip()
        normalized_password = password.strip()
        normalized_phone = phone.strip() if phone else None
        normalized_family_name = family_name.strip() if family_name else f"{normalized_name} 가족"
        validate_non_empty_string(normalized_family_name, "family_name")

        now = datetime.now(timezone.utc)
        verification = self.email_verification_repository.find_latest_verified_unused_by_email(
            normalized_email,
            now
        )
        if not verification:
            raise BadRequestException("Email verification must be completed before registration")

        existing_email_user = self.user_repository.find_by_email(normalized_email)
        if existing_email_user and existing_email_user.kakao_user_id != normalized_kakao_user_id:
            raise ConflictException("Email is already registered")

        existing_user = self.user_repository.find_by_kakao_user_id(normalized_kakao_user_id)
        if existing_user and existing_user.email and existing_user.email != normalized_email:
            raise ConflictException("kakao_user_id is already linked to another email")

        user = existing_user or existing_email_user

        try:
            if user is None:
                user = self.user_repository.create(
                    kakao_user_id=normalized_kakao_user_id,
                    name=normalized_name,
                    email=normalized_email,
                    password_hash=hash_password(normalized_password),
                    phone=normalized_phone,
                    age=age
                )
            else:
                if self.family_member_repository.exists_by_user_id(user.id):
                    raise ConflictException("User is already registered")

                self.user_repository.update_profile(
                    user=user,
                    name=normalized_name,
                    email=normalized_email,
                    password_hash=hash_password(normalized_password),
                    phone=normalized_phone,
                    age=age
                )

            family = self.family_repository.create(normalized_family_name, user.id)
            family_member = self.family_member_repository.create(family.id, user.id, "owner")
            self.email_verification_repository.mark_used(verification, now)
            self.db.commit()
            self.db.refresh(user)
            self.db.refresh(family)
            self.db.refresh(family_member)

            return RegisterResponse(
                user_id=user.id,
                kakao_user_id=user.kakao_user_id,
                email=user.email,
                name=user.name,
                family_id=family.id,
                family_name=family.family_name,
                family_member_id=family_member.id,
                role=family_member.role,
                created_at=user.created_at
            )
        except IntegrityError as e:
            self.db.rollback()
            # DB 제약조건 위반으로 인한 중복 가입 시도
            if "email" in str(e.orig).lower() or "kakao_user_id" in str(e.orig).lower():
                raise ConflictException("User already exists")
            raise
        except Exception:
            self.db.rollback()
            raise

    def login(self, email: str, password: str) -> AuthTokenResponse:
        validate_email(email)
        validate_password(password)

        user = self.user_repository.find_by_email(email.strip())
        if not user or not verify_password(password.strip(), user.password_hash):
            raise UnauthorizedException("Invalid email or password")

        try:
            issued_tokens = self._issue_token_pair(user)
            self.db.commit()
            return issued_tokens
        except Exception:
            self.db.rollback()
            raise

    def refresh(self, refresh_token: str) -> AuthTokenResponse:
        payload = decode_token(refresh_token.strip(), expected_type="refresh")
        token_id = payload.get("jti")
        user_id = payload.get("sub")
        if not token_id or not user_id:
            raise UnauthorizedException("Invalid refresh token payload")

        refresh_token_row = self.refresh_token_repository.find_by_token_id(token_id)
        if not refresh_token_row or refresh_token_row.is_revoked:
            raise UnauthorizedException("Refresh token is revoked")

        now = datetime.now(timezone.utc)
        expires_at = normalize_datetime_required(refresh_token_row.expires_at)
        if expires_at <= now:
            raise UnauthorizedException("Refresh token has expired")

        user = self.user_repository.find_by_id(int(user_id))
        if not user or refresh_token_row.user_id != user.id:
            raise UnauthorizedException("Refresh token is invalid")

        try:
            self.refresh_token_repository.revoke(refresh_token_row, now)
            issued_tokens = self._issue_token_pair(user, revoke_existing=False)
            self.db.commit()
            return issued_tokens
        except Exception:
            self.db.rollback()
            raise

    def logout(self, user_id: int, refresh_token: str) -> LogoutResponse:
        payload = decode_token(refresh_token.strip(), expected_type="refresh")
        token_id = payload.get("jti")
        token_user_id = payload.get("sub")
        if not token_id or not token_user_id or int(token_user_id) != user_id:
            raise UnauthorizedException("Refresh token is invalid")

        refresh_token_row = self.refresh_token_repository.find_by_token_id(token_id)
        if not refresh_token_row:
            raise NotFoundException("Refresh token not found")

        if refresh_token_row.user_id != user_id:
            raise UnauthorizedException("Refresh token is invalid")

        try:
            if not refresh_token_row.is_revoked:
                self.refresh_token_repository.revoke(refresh_token_row, datetime.now(timezone.utc))
            self.db.commit()
            return LogoutResponse(logged_out=True)
        except Exception:
            self.db.rollback()
            raise

    @staticmethod
    def _generate_verification_code() -> str:
        return str(secrets.randbelow(900000) + 100000)


    def _issue_token_pair(self, user, revoke_existing: bool = True) -> AuthTokenResponse:
        issued_at = datetime.now(timezone.utc)
        if revoke_existing:
            self.refresh_token_repository.revoke_all_active_by_user_id(user.id, issued_at)

        refresh_token_id = generate_token_id()
        access_token, access_token_expires_at = create_access_token(user.id)
        refresh_token, refresh_token_expires_at = create_refresh_token(user.id, refresh_token_id)
        self.refresh_token_repository.create(
            user_id=user.id,
            token_id=refresh_token_id,
            created_at=issued_at,
            expires_at=refresh_token_expires_at
        )

        return AuthTokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            access_token_expires_at=access_token_expires_at,
            refresh_token_expires_at=refresh_token_expires_at,
            user_id=user.id,
            kakao_user_id=user.kakao_user_id,
            email=user.email,
            name=user.name
        )
