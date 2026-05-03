"""
Email verification data access layer

Database access layer for email verification process in Smart Scan system.
Securely manages generation, verification, and usage process of 6-digit verification codes to enhance spam prevention and security.

Main features:
- Email-specific verification code generation and management
- Invalidation of existing unused codes (security enhancement)
- Code verification and usage status tracking
- Automatic cleanup based on expiration time

Business rules:
- Only one valid verification code exists per email
- Separate tracking of verification completion and usage completion
- Minimize security risks through time-based expiration
- Ensure consistency with latest code priority lookup

Data flow:
1. Invalidate existing incomplete codes when verification requested
2. Generate and send new verification code
3. Perform verification when user inputs code
4. Process code usage when registration completes

Security enhancement:
- Prevent duplicate codes through concurrency control
- Automatic invalidation of expired codes
- Prevent reuse of used codes
"""

from datetime import datetime
from sqlalchemy.orm import Session
from backend.models.email_verification import EmailVerification


class EmailVerificationRepository:
    """
    Email verification data access class

    Database access layer that manages the entire lifecycle of email verification codes.
    """
    def __init__(self, db: Session):
        """Inject database session"""
        self.db = db

    def invalidate_pending_by_email(self, email: str, now: datetime) -> None:
        """
        Invalidate all incomplete verification codes for specified email

        Before sending new verification code, expire all existing unused codes
        to enhance security and prevent duplicate code sending.

        Args:
            email: Email address to invalidate verification codes for
            now: Current time (UTC)

        Invalidation targets:
            - Not verified (verified_at IS NULL)
            - Not used (used_at IS NULL)
            - Not yet expired (expires_at > now)
        """
        self.db.query(EmailVerification).filter(
            EmailVerification.email == email,
            EmailVerification.verified_at.is_(None),
            EmailVerification.used_at.is_(None),
            EmailVerification.expires_at > now
        ).update(
            {EmailVerification.expires_at: now},
            synchronize_session=False
        )

    def create(self, email: str, code: str, expires_at: datetime) -> EmailVerification:
        """
        Create new email verification code

        Args:
            email: Target email address for verification
            code: 6-digit numeric verification code
            expires_at: Code expiration time (UTC)

        Returns:
            EmailVerification: Created verification code entity
        """
        verification = EmailVerification(
            email=email,
            code=code,
            expires_at=expires_at
        )
        self.db.add(verification)
        self.db.flush()
        return verification

    def find_latest_by_email_and_code(self, email: str, code: str) -> EmailVerification | None:
        """
        Retrieve latest verification code by email and code

        To verify user-input verification code,
        retrieves the latest code for the email.

        Args:
            email: Verification email address
            code: Verification code to verify

        Returns:
            EmailVerification | None: Matching latest verification code or None
        """
        return self.db.query(EmailVerification).filter(
            EmailVerification.email == email,
            EmailVerification.code == code
        ).order_by(
            EmailVerification.id.desc()
        ).first()

    def find_latest_verified_unused_by_email(
        self,
        email: str,
        now: datetime
    ) -> EmailVerification | None:
        """
        Retrieve verified unused verification code for email

        To confirm email verification completion during registration,
        retrieves code that is verified but not yet used.

        Args:
            email: Verification email address
            now: Current time (UTC, for expiration check)

        Returns:
            EmailVerification | None: Available verification code or None

        Query conditions:
            - Verification complete (verified_at IS NOT NULL)
            - Not yet used (used_at IS NULL)
            - Not expired (expires_at > now)
        """
        return self.db.query(EmailVerification).filter(
            EmailVerification.email == email,
            EmailVerification.verified_at.is_not(None),
            EmailVerification.used_at.is_(None),
            EmailVerification.expires_at > now
        ).order_by(
            EmailVerification.id.desc()
        ).first()

    def mark_verified(self, verification: EmailVerification, verified_at: datetime) -> EmailVerification:
        """
        Mark verification code as verification complete

        When user inputs correct verification code,
        records the verification completion time.

        Args:
            verification: Verification code entity to mark as verified
            verified_at: Verification completion time (UTC)

        Returns:
            EmailVerification: Updated verification code entity
        """
        verification.verified_at = verified_at
        self.db.flush()
        return verification

    def mark_used(self, verification: EmailVerification, used_at: datetime) -> EmailVerification:
        """
        Mark verification code as usage complete

        When registration is successfully completed,
        process verification code as usage complete to prevent reuse.

        Args:
            verification: Verification code entity to mark as used
            used_at: Usage completion time (UTC)

        Returns:
            EmailVerification: Updated verification code entity
        """
        verification.used_at = used_at
        self.db.flush()
        return verification
