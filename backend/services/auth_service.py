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
    decode_kakao_link_token,
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
    LinkKakaoResponse,
    LogoutResponse,
    RegisterResponse,
    SendVerificationEmailResponse,
    VerifyEmailResponse,
)
from backend.services.email_service import EmailService


class AuthService:
    """
    Service class for authentication-related business logic

    This service manages the entire flow of user registration, login, token management, and email verification.
    Supports Kakao social login and email-based registration, using JWT-based authentication.

    Design principles:
    - Mandatory email verification: Prevent spam and secure valid contact information
    - Kakao ID and email integration: Balance social login convenience with independent account management
    - Family-based service: Automatically create family and grant owner privileges upon registration
    - Enhanced security: Refresh token rotation, password hashing, duplicate registration prevention
    """
    def __init__(self, db: Session):
        """Initialize repositories and services through dependency injection"""
        self.db = db
        self.user_repository = UserRepository(db)
        self.family_repository = FamilyRepository(db)
        self.family_member_repository = FamilyMemberRepository(db)
        self.email_verification_repository = EmailVerificationRepository(db)
        self.refresh_token_repository = RefreshTokenRepository(db)
        self.email_service = EmailService()

    def send_verification_email(self, email: str) -> SendVerificationEmailResponse:
        """
        Send email verification code

        Mandatory step before registration, generates and sends a 6-digit numeric code via email.
        Invalidates existing unused verification codes to enhance security.
        """
        validate_email(email)
        normalized_email = email.strip()

        # Check for duplicate email - cannot send verification code to already registered email
        existing_user = self.user_repository.find_by_email(normalized_email)
        if existing_user:
            raise ConflictException("Email is already registered")

        # Generate verification code and set expiration time
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=settings.EMAIL_VERIFICATION_EXPIRE_MINUTES)
        code = self._generate_verification_code()

        try:
            # Invalidate existing incomplete verification codes then generate and send new code
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
        """
        이메일 인증 코드 검증

        사용자가 입력한 6자리 코드를 검증하여 이메일 소유권을 확인한다.
        인증 성공 시 회원가입이 가능한 상태가 된다.
        """
        validate_email(email)
        validate_verification_code(code)
        normalized_email = email.strip()
        normalized_code = code.strip()

        # 인증 코드 조회 및 유효성 검사
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
            # 인증 완료 처리 (중복 인증 시도도 성공으로 처리)
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
        """
        회원가입 처리

        이메일 인증이 완료된 사용자만 가입할 수 있다.
        카카오 ID와 이메일 연동을 지원하며, 가입과 동시에 가족을 생성한다.
        기존 부분 가입 사용자(카카오만 또는 이메일만)의 정보 통합도 처리한다.
        """
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
        normalized_password = password  # 비밀번호는 공백 포함 원본 그대로 사용
        normalized_phone = phone.strip() if phone else None
        # 가족명 기본값 설정 (미입력시 "사용자명 가족"으로 자동 생성)
        normalized_family_name = family_name.strip() if family_name else f"{normalized_name} 가족"
        validate_non_empty_string(normalized_family_name, "family_name")

        # 이메일 인증 완료 확인 (회원가입 전 필수 조건)
        now = datetime.now(timezone.utc)
        verification = self.email_verification_repository.find_latest_verified_unused_by_email(
            normalized_email,
            now
        )
        if not verification:
            raise BadRequestException("Email verification must be completed before registration")

        # 중복 가입 방지 및 부분 가입 사용자 통합 로직
        existing_email_user = self.user_repository.find_by_email(normalized_email)
        if existing_email_user and existing_email_user.kakao_user_id != normalized_kakao_user_id:
            raise ConflictException("Email is already registered")

        existing_user = self.user_repository.find_by_kakao_user_id(normalized_kakao_user_id)
        if existing_user and existing_user.email and existing_user.email != normalized_email:
            raise ConflictException("kakao_user_id is already linked to another email")

        # 기존 사용자 정보 통합 (카카오만 있거나 이메일만 있는 경우)
        user = existing_user or existing_email_user

        try:
            # 신규 사용자 생성 또는 기존 사용자 정보 업데이트
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
                # 이미 완전 가입된 사용자인지 확인
                if self.family_member_repository.exists_by_user_id(user.id):
                    raise ConflictException("User is already registered")

                # 부분 가입 사용자의 정보 완성
                self.user_repository.update_profile(
                    user=user,
                    name=normalized_name,
                    email=normalized_email,
                    password_hash=hash_password(normalized_password),
                    phone=normalized_phone,
                    age=age
                )

            # 가족 생성 및 소유자 권한 부여 (Smart Scan은 가족 단위 서비스)
            family = self.family_repository.create(normalized_family_name, user.id)
            family_member = self.family_member_repository.create(family.id, user.id, "owner")
            # 사용한 이메일 인증 코드 표시
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
            # DB 제약조건 위반으로 인한 중복 가입 시도 (동시성 문제 대응)
            if "email" in str(e.orig).lower() or "kakao_user_id" in str(e.orig).lower():
                raise ConflictException("User already exists")
            raise
        except Exception:
            self.db.rollback()
            raise

    def login(self, email: str, password: str) -> AuthTokenResponse:
        """
        사용자 로그인

        이메일과 비밀번호로 인증하여 JWT 토큰 쌍을 발급한다.
        기존 refresh token을 모두 무효화하여 보안을 강화한다.
        """
        validate_email(email)
        validate_password(password)

        # 사용자 인증 (이메일 또는 비밀번호 오류 시 동일한 답안으로 보안 강화)
        user = self.user_repository.find_by_email(email.strip())
        if not user or not verify_password(password, user.password_hash):
            raise UnauthorizedException("Invalid email or password")

        try:
            # 토큰 쌍 발급 (기존 refresh token 모두 무효화)
            issued_tokens = self._issue_token_pair(user)
            self.db.commit()
            return issued_tokens
        except Exception:
            self.db.rollback()
            raise

    def refresh(self, refresh_token: str) -> AuthTokenResponse:
        """
        Access token 갱신

        유효한 refresh token을 사용하여 새로운 JWT 토큰 쌍을 발급한다.
        Refresh token rotation을 사용하여 기존 token은 무효화하고 새 token을 발급한다.
        """
        # JWT 토큰 디코딩 및 페이로드 검증
        payload = decode_token(refresh_token.strip(), expected_type="refresh")
        token_id = payload.get("jti")
        user_id = payload.get("sub")
        if not token_id or not user_id:
            raise UnauthorizedException("Invalid refresh token payload")

        # DB에서 refresh token 조회 및 유효성 검사
        refresh_token_row = self.refresh_token_repository.find_by_token_id(token_id)
        if not refresh_token_row or refresh_token_row.is_revoked:
            raise UnauthorizedException("Refresh token is revoked")

        # 만료 시간 및 소유자 검증
        now = datetime.now(timezone.utc)
        expires_at = normalize_datetime_required(refresh_token_row.expires_at)
        if expires_at <= now:
            raise UnauthorizedException("Refresh token has expired")

        user = self.user_repository.find_by_id(int(user_id))
        if not user or refresh_token_row.user_id != user.id:
            raise UnauthorizedException("Refresh token is invalid")

        try:
            # 기존 refresh token 무효화 후 새 token pair 발급 (rotation)
            self.refresh_token_repository.revoke(refresh_token_row, now)
            issued_tokens = self._issue_token_pair(user, revoke_existing=False)
            self.db.commit()
            return issued_tokens
        except Exception:
            self.db.rollback()
            raise

    def logout(self, user_id: int, refresh_token: str) -> LogoutResponse:
        """
        사용자 로그아웃

        제공된 refresh token을 무효화하여 로그아웃을 처리한다.
        토큰 검증을 통해 정당한 사용자의 요청인지 확인한다.
        """
        # JWT 토큰 디코딩 및 요청자 검증
        payload = decode_token(refresh_token.strip(), expected_type="refresh")
        token_id = payload.get("jti")
        token_user_id = payload.get("sub")
        if not token_id or not token_user_id or int(token_user_id) != user_id:
            raise UnauthorizedException("Refresh token is invalid")

        # DB에서 refresh token 조회 및 소유자 검증
        refresh_token_row = self.refresh_token_repository.find_by_token_id(token_id)
        if not refresh_token_row:
            raise NotFoundException("Refresh token not found")

        if refresh_token_row.user_id != user_id:
            raise UnauthorizedException("Refresh token is invalid")

        try:
            # 미처리 상태의 refresh token만 무효화 (중복 로그아웃 방지)
            if not refresh_token_row.is_revoked:
                self.refresh_token_repository.revoke(refresh_token_row, datetime.now(timezone.utc))
            self.db.commit()
            return LogoutResponse(logged_out=True)
        except Exception:
            self.db.rollback()
            raise

    def link_kakao(self, user_id: int, token: str) -> LinkKakaoResponse:
        """
        카카오 계정 연동 (magic link)

        챗봇 Lambda가 발급한 단기 JWT(토큰)를 검증하여 현재 로그인 사용자의
        kakao_user_id 를 실제 카카오 UID로 업데이트한다.

        동작 규칙:
        - 토큰이 유효하지 않거나 만료된 경우 UnauthorizedException
        - 이미 동일한 kakao_user_id로 연동되어 있으면 멱등 성공 처리
        - 다른 사용자가 같은 kakao_user_id로 이미 연동되어 있으면 ConflictException
        - 현재 사용자의 kakao_user_id 가 실제 UID(= pending_xxx 가 아님)로 이미
          설정되어 있으면 덮어쓰지 않고 ConflictException. placeholder(pending_xxx)
          상태일 때만 덮어쓰기 허용
        """
        validate_non_empty_string(token, "token")

        # 토큰 검증 및 kakao_user_id 추출
        payload = decode_kakao_link_token(token.strip())
        new_kakao_user_id = payload["kakao_user_id"].strip()
        if not new_kakao_user_id:
            raise UnauthorizedException("Invalid kakao link token payload")

        # 현재 사용자 조회
        user = self.user_repository.find_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")

        # 멱등 처리: 이미 동일한 값이면 그대로 성공
        if user.kakao_user_id == new_kakao_user_id:
            return LinkKakaoResponse(
                user_id=user.id,
                kakao_user_id=user.kakao_user_id,
                linked=True,
            )

        # 다른 사용자가 이미 이 kakao_user_id 를 점유하고 있는지 확인
        conflicting_user = self.user_repository.find_by_kakao_user_id(new_kakao_user_id)
        if conflicting_user and conflicting_user.id != user.id:
            raise ConflictException("kakao_user_id is already linked to another user")

        # 실제 UID 가 이미 설정된 계정이라면 덮어쓰기 금지
        # (placeholder "pending_xxx" 상태에서만 실제 UID 로 교체 허용)
        if user.kakao_user_id and not user.kakao_user_id.startswith("pending_"):
            raise ConflictException("User is already linked to a kakao account")

        try:
            self.user_repository.update_kakao_user_id(user, new_kakao_user_id)
            self.db.commit()
            self.db.refresh(user)
            return LinkKakaoResponse(
                user_id=user.id,
                kakao_user_id=user.kakao_user_id,
                linked=True,
            )
        except IntegrityError as e:
            self.db.rollback()
            # 동시성으로 인한 UNIQUE 제약 위반 대응
            if "kakao_user_id" in str(e.orig).lower():
                raise ConflictException("kakao_user_id is already linked to another user")
            raise
        except Exception:
            self.db.rollback()
            raise

    @staticmethod
    def _generate_verification_code() -> str:
        """안전한 6자리 숫자 인증 코드 생성 (100000~999999)"""
        return str(secrets.randbelow(900000) + 100000)


    def _issue_token_pair(self, user, revoke_existing: bool = True) -> AuthTokenResponse:
        """
        JWT 토큰 쌍 (access + refresh) 발급

        기본적으로 기존 refresh token들을 모두 무효화하는 single session 정책을 사용.
        refresh 시에만 revoke_existing=False로 사용하여 단일 토큰만 교체.
        """
        # 기존 활성 refresh token 무효화 (single session 정책)
        issued_at = datetime.now(timezone.utc)
        if revoke_existing:
            self.refresh_token_repository.revoke_all_active_by_user_id(user.id, issued_at)

        # 새 JWT 토큰 쌍 생성 및 DB에 refresh token 정보 저장
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
