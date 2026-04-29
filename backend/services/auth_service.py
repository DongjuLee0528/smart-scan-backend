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
        Verify email authentication code

        Verify 6-digit code entered by user to confirm email ownership.
        Upon successful verification, registration becomes possible.
        """
        validate_email(email)
        validate_verification_code(code)
        normalized_email = email.strip()
        normalized_code = code.strip()

        # Find verification code and validate
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
            # Complete verification process (handle duplicate verification attempts as success)
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
        Process user registration

        Only users who have completed email verification can register.
        Supports KakaoTalk ID and email integration, creating family upon registration.
        Also handles information integration of existing partial users (KakaoTalk-only or email-only).
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
        normalized_password = password  # Use password as-is including whitespace
        normalized_phone = phone.strip() if phone else None
        # Set default family name (auto-generate as "Username Family" if not entered)
        normalized_family_name = family_name.strip() if family_name else f"{normalized_name} Family"
        validate_non_empty_string(normalized_family_name, "family_name")

        # Verify email authentication completion (mandatory before registration)
        now = datetime.now(timezone.utc)
        verification = self.email_verification_repository.find_latest_verified_unused_by_email(
            normalized_email,
            now
        )
        if not verification:
            raise BadRequestException("Email verification must be completed before registration")

        # Prevent duplicate registration and integrate partial users
        existing_email_user = self.user_repository.find_by_email(normalized_email)
        if existing_email_user and existing_email_user.kakao_user_id != normalized_kakao_user_id:
            raise ConflictException("Email is already registered")

        existing_user = self.user_repository.find_by_kakao_user_id(normalized_kakao_user_id)
        if existing_user and existing_user.email and existing_user.email != normalized_email:
            raise ConflictException("kakao_user_id is already linked to another email")

        # Integrate existing user info (KakaoTalk-only or email-only cases)
        user = existing_user or existing_email_user

        try:
            # Create new user or update existing user info
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
                # Check if user is already fully registered
                if self.family_member_repository.exists_by_user_id(user.id):
                    raise ConflictException("User is already registered")

                # Complete partial user information
                self.user_repository.update_profile(
                    user=user,
                    name=normalized_name,
                    email=normalized_email,
                    password_hash=hash_password(normalized_password),
                    phone=normalized_phone,
                    age=age
                )

            # Create family and grant owner privileges (Smart Scan is family-based service)
            family = self.family_repository.create(normalized_family_name, user.id)
            family_member = self.family_member_repository.create(family.id, user.id, "owner")
            # Mark used email verification code
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
            # Handle duplicate registration due to DB constraint violations (concurrency handling)
            if "email" in str(e.orig).lower() or "kakao_user_id" in str(e.orig).lower():
                raise ConflictException("User already exists")
            raise
        except Exception:
            self.db.rollback()
            raise

    def login(self, email: str, password: str) -> AuthTokenResponse:
        """
        User login

        Authenticate with email and password to issue JWT token pair.
        Enhance security by invalidating all existing refresh tokens.
        """
        validate_email(email)
        validate_password(password)

        # User authentication (enhance security with same response for email or password errors)
        user = self.user_repository.find_by_email(email.strip())
        if not user or not verify_password(password, user.password_hash):
            raise UnauthorizedException("Invalid email or password")

        try:
            # Issue token pair (invalidate all existing refresh tokens)
            issued_tokens = self._issue_token_pair(user)
            self.db.commit()
            return issued_tokens
        except Exception:
            self.db.rollback()
            raise

    def refresh(self, refresh_token: str) -> AuthTokenResponse:
        """
        Refresh access token

        Use valid refresh token to issue new JWT token pair.
        Use refresh token rotation to invalidate existing token and issue new token.
        """
        # Decode JWT token and validate payload
        payload = decode_token(refresh_token.strip(), expected_type="refresh")
        token_id = payload.get("jti")
        user_id = payload.get("sub")
        if not token_id or not user_id:
            raise UnauthorizedException("Invalid refresh token payload")

        # Query refresh token from DB and validate
        refresh_token_row = self.refresh_token_repository.find_by_token_id(token_id)
        if not refresh_token_row or refresh_token_row.is_revoked:
            raise UnauthorizedException("Refresh token is revoked")

        # Validate expiration time and owner
        now = datetime.now(timezone.utc)
        expires_at = normalize_datetime_required(refresh_token_row.expires_at)
        if expires_at <= now:
            raise UnauthorizedException("Refresh token has expired")

        user = self.user_repository.find_by_id(int(user_id))
        if not user or refresh_token_row.user_id != user.id:
            raise UnauthorizedException("Refresh token is invalid")

        try:
            # Invalidate existing refresh token then issue new token pair (rotation)
            self.refresh_token_repository.revoke(refresh_token_row, now)
            issued_tokens = self._issue_token_pair(user, revoke_existing=False)
            self.db.commit()
            return issued_tokens
        except Exception:
            self.db.rollback()
            raise

    def logout(self, user_id: int, refresh_token: str) -> LogoutResponse:
        """
        User logout

        Process logout by invalidating provided refresh token.
        Verify legitimate user request through token validation.
        """
        # Decode JWT token and verify requester
        payload = decode_token(refresh_token.strip(), expected_type="refresh")
        token_id = payload.get("jti")
        token_user_id = payload.get("sub")
        if not token_id or not token_user_id or int(token_user_id) != user_id:
            raise UnauthorizedException("Refresh token is invalid")

        # Query refresh token from DB and verify owner
        refresh_token_row = self.refresh_token_repository.find_by_token_id(token_id)
        if not refresh_token_row:
            raise NotFoundException("Refresh token not found")

        if refresh_token_row.user_id != user_id:
            raise UnauthorizedException("Refresh token is invalid")

        try:
            # Only invalidate unprocessed refresh tokens (prevent duplicate logout)
            if not refresh_token_row.is_revoked:
                self.refresh_token_repository.revoke(refresh_token_row, datetime.now(timezone.utc))
            self.db.commit()
            return LogoutResponse(logged_out=True)
        except Exception:
            self.db.rollback()
            raise

    def link_kakao(self, user_id: int, token: str) -> LinkKakaoResponse:
        """
        Link KakaoTalk account (magic link)

        Verify short-term JWT (token) issued by chatbot Lambda to update
        current logged-in user's kakao_user_id to actual KakaoTalk UID.

        Behavior rules:
        - UnauthorizedException if token is invalid or expired
        - Idempotent success if already linked with same kakao_user_id
        - ConflictException if another user is already linked with same kakao_user_id
        - If current user's kakao_user_id is already set to actual UID (not pending_xxx),
          don't overwrite and throw ConflictException. Only allow overwrite when in
          placeholder (pending_xxx) state
        """
        validate_non_empty_string(token, "token")

        # Validate token and extract kakao_user_id
        payload = decode_kakao_link_token(token.strip())
        new_kakao_user_id = payload["kakao_user_id"].strip()
        if not new_kakao_user_id:
            raise UnauthorizedException("Invalid kakao link token payload")

        # Query current user
        user = self.user_repository.find_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")

        # Idempotent handling: success as-is if already same value
        if user.kakao_user_id == new_kakao_user_id:
            return LinkKakaoResponse(
                user_id=user.id,
                kakao_user_id=user.kakao_user_id,
                linked=True,
            )

        # Check if another user already occupies this kakao_user_id
        conflicting_user = self.user_repository.find_by_kakao_user_id(new_kakao_user_id)
        if conflicting_user and conflicting_user.id != user.id:
            raise ConflictException("kakao_user_id is already linked to another user")

        # Prohibit overwrite if actual UID is already set
        # (only allow replacement from placeholder "pending_xxx" state to actual UID)
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
            # Handle UNIQUE constraint violations due to concurrency
            if "kakao_user_id" in str(e.orig).lower():
                raise ConflictException("kakao_user_id is already linked to another user")
            raise
        except Exception:
            self.db.rollback()
            raise

    @staticmethod
    def _generate_verification_code() -> str:
        """Generate secure 6-digit numeric verification code (100000~999999)"""
        return str(secrets.randbelow(900000) + 100000)


    def _issue_token_pair(self, user, revoke_existing: bool = True) -> AuthTokenResponse:
        """
        Issue JWT token pair (access + refresh)

        Uses single session policy that invalidates all existing refresh tokens by default.
        Only during refresh, use revoke_existing=False to replace single token only.
        """
        # Invalidate existing active refresh tokens (single session policy)
        issued_at = datetime.now(timezone.utc)
        if revoke_existing:
            self.refresh_token_repository.revoke_all_active_by_user_id(user.id, issued_at)

        # Generate new JWT token pair and store refresh token info in DB
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
