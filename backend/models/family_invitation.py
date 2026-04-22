"""
가족 초대 데이터베이스 모델

SmartScan 시스템에서 가족 그룹 초대를 관리하는 데이터베이스 모델입니다.
가족 소유자가 이메일로 다른 사용자를 초대하면 토큰 기반 수락/거절 플로우를 제공합니다.

비즈니스 모델:
- 가족 소유자만 초대 발송 가능
- 초대는 7일 후 자동 만료 (lazy expire 방식: by-token 조회 시 처리)
- 수락 시 기존 family_member 레코드를 교체하여 새 가족으로 이동
- 한 (family, email) 쌍당 하나의 pending 초대만 허용

status 값: pending / accepted / declined / cancelled / expired
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.common.db import Base


class FamilyInvitation(Base):
    """
    가족 초대 모델

    이메일 기반 초대 토큰을 발행하여 수신자가 앱에서 가족에 합류하도록 안내합니다.
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
