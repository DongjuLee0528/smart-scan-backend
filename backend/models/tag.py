"""
가상 태그 데이터베이스 모델

사용자가 생성하는 가상 태그를 나타내는 데이터베이스 모델입니다.
실제 물리적 RFID 태그와 연결되기 전 단계의 논리적 태그 정보를 관리합니다.

비즈니스 모델:
- 가상 태그: 사용자가 웹에서 생성하는 논리적 태그
- 물리적 연결: 나중에 실제 RFID 태그와 tag_uid로 매핑
- 사용자 소유권: 각 태그는 특정 사용자가 소유
- 가족 공유: 가족 구성원들이 서로의 태그 조회 가능

데이터 속성:
- tag_uid: 전체 시스템에서 고유한 식별자
- 리브 아이템 연결: 아직 아이템과 연결되지 않은 상태 지원
- 비활성화: 사용하지 않는 태그를 비활성화하여 숨김 처리

관계 연결:
- N:1 관계: family, owner_user
"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.common.db import Base


class Tag(Base):
    """
    가상 태그 모델

    사용자가 생성한 가상 태그 정보를 나타내는 논리적 모델입니다.
    """
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    tag_uid = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # relationships
    family = relationship("Family", back_populates="tags")
    owner = relationship("User", back_populates="owned_tags")
    device = relationship("Device", back_populates="tags")
