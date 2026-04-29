"""
Family invitation database model

Database model for managing family group invitations in SmartScan system.
When family owners invite other users by email, provides token-based accept/decline flow.

Business model:
- Only family owners can send invitations
- Invitations auto-expire after 7 days (lazy expire: handled during by-token lookup)
- When accepted, replaces existing family_member record to move to new family
- Only one pending invitation allowed per (family, email) pair

status values: pending / accepted / declined / cancelled / expired
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.common.db import Base


class FamilyInvitation(Base):
    """
    Family invitation model

    Issues email-based invitation tokens to guide recipients to join families in the app.
    """
    __tablename__ = "family_invitations"
    __table_args__ = (
        Index("idx_family_invitations_family_email_status", "family_id", "email", "status"),
        Index("idx_family_invitations_expires_at", "expires_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id", ondelete="CASCADE"), nullable=False, index=True)
    inviter_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), nullable=False)
    suggested_name = Column(String(100), nullable=True)
    suggested_phone = Column(String(30), nullable=True)
    suggested_age = Column(Integer, nullable=True)
    token = Column(UUID(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    status = Column(String(20), nullable=False, default="pending")
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    declined_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    # relationships
    family = relationship("Family", foreign_keys=[family_id])
    inviter = relationship("User", foreign_keys=[inviter_user_id])
