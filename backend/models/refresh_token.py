"""
JWT Refresh Token Database Model

Database model for securely managing refresh tokens in the Smart Scan system's JWT-based authentication.
Serves as a security-enhanced token storage for access token reissuance and session management.

Business Model:
- Token rotation: Used refresh tokens are immediately invalidated and new tokens are issued
- Security enhancement: Expiration time management to minimize damage from token theft
- Session tracking: Manage active sessions and login devices per user

Token Lifecycle:
1. Issuance (created_at): Create new refresh token on successful login
2. Usage: Reissue access token when expired using refresh token
3. Rotation: Invalidate used token and issue new token
4. Expiration/Invalidation: Invalidate token on time expiration or logout

Security Features:
- Token identification and duplication prevention through unique token_id
- Immediate token invalidation through is_revoked flag
- Minimize security risks through automatic cleanup based on expiration time
- Detect abnormal access through per-user token tracking

Relationship Connections:
- N:1 relationship: user (token owner)
"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from backend.common.db import Base


class RefreshToken(Base):
    """
    JWT Refresh Token Model

    Stores user refresh token information and manages token lifecycle.
    """
    __tablename__ = "refresh_tokens"

    # Basic identifier
    id = Column(Integer, primary_key=True, index=True)  # Internal token record ID

    # User connection
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # Token owner user ID

    # Token information
    token_id = Column(String(255), unique=True, nullable=False, index=True)  # Unique token identifier (UUID)

    # Time management
    created_at = Column(DateTime(timezone=True), nullable=False)  # Token issuance time
    expires_at = Column(DateTime(timezone=True), nullable=False)  # Token expiration time

    # Status management
    is_revoked = Column(Boolean, default=False, nullable=False)  # Token revocation status
    revoked_at = Column(DateTime(timezone=True), nullable=True)  # Token revocation time

    # Relationship definitions
    user = relationship("User")  # Token owner
