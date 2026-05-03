"""
Email verification database model

Manages verification codes for email ownership confirmation during Smart Scan system registration.
Tracks generation, verification, and usage status of 6-digit numeric verification codes to ensure secure registration.

Business model:
- Verification code: One-time use code consisting of 6 digits
- Expiration time: Automatic expiration after configurable time
- Verification status: Separate management of verification completion and usage completion
- Security enhancement: Prevention of duplicate usage and time-based expiration

Data lifecycle:
1. Creation (created_at): User requests email verification
2. Verification (verified_at): User inputs correct code
3. Usage (used_at): Code consumed when actual registration completes
4. Expiration (expires_at): Automatic invalidation after set time

Relationship connections:
- Independent table (no foreign key relationships)
- Logical connection to users through email address
"""

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func
from backend.common.db import Base


class EmailVerification(Base):
    """
    Email verification model

    Stores and manages verification code information for email ownership confirmation during registration.
    """
    __tablename__ = "email_verifications"

    # Primary identifier
    id = Column(Integer, primary_key=True, index=True)  # Internal verification ID

    # Verification target information
    email = Column(String(255), nullable=False, index=True)  # Email address to be verified
    code = Column(String(6), nullable=False)  # 6-digit numeric verification code

    # Time management
    expires_at = Column(DateTime(timezone=True), nullable=False)  # Verification code expiration time
    verified_at = Column(DateTime(timezone=True), nullable=True)  # Code verification completion time
    used_at = Column(DateTime(timezone=True), nullable=True)  # Time when used for registration
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)  # Code creation time
