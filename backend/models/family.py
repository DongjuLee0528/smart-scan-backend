"""
가족 그룹 데이터베이스 모델

SmartScan 시스템의 핵심 개념인 가족 그룹을 나타내는 데이터베이스 모델입니다.
가족 단위로 RFID 디바이스와 소지품을 공유하여 관리합니다.

비즈니스 모델:
- 가족 소유자(Owner): 가족 그룹을 생성한 사용자, 모든 관리 권한 소유
- 가족 구성원: 가족에 초대된 사용자들, 제한된 권한
- 디바이스 공유: 한 가족당 하나의 RFID 리더기를 공동 사용
- 소지품 공유: 가족 구성원 모두가 서로의 소지품 상태 확인 가능

관계 연결:
- 1:N 관계: devices, tags, family_members
- N:1 관계: owner (User)
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.common.db import Base


class Family(Base):
    """
    가족 그룹 모델

    가족 단위로 RFID 시스템을 공유하여 사용하는 그룹을 나타냅니다.
    """
    __tablename__ = "families"

    id = Column(Integer, primary_key=True, index=True)
    family_name = Column(String(255), nullable=False)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # relationships
    devices = relationship("Device", back_populates="family")
    tags = relationship("Tag", back_populates="family")
    owner = relationship("User", back_populates="owned_families", foreign_keys=[owner_user_id])
    family_members = relationship("FamilyMember", back_populates="family")
