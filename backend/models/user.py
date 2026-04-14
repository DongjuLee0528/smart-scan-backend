"""
사용자 모델

SmartScan 시스템의 사용자 정보를 저장하는 데이터베이스 모델입니다.
카카오톡 봇 연동과 웹 서비스 사용자 모두를 지원합니다.
"""

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.common.db import Base


class User(Base):
    __tablename__ = "users"

    # 기본 식별자
    id = Column(Integer, primary_key=True, index=True)  # 내부 사용자 ID

    # 카카오톡 연동 정보
    kakao_user_id = Column(String(255), unique=True, nullable=False, index=True)  # 카카오 사용자 고유 ID

    # 사용자 기본 정보
    name = Column(String(255), nullable=True)  # 사용자 이름
    email = Column(String(255), unique=True, nullable=True, index=True)  # 이메일 주소 (웹 로그인용)
    password_hash = Column(String(255), nullable=True)  # 암호화된 비밀번호 (웹 로그인용)
    phone = Column(String(50), nullable=True)  # 휴대폰 번호
    age = Column(Integer, nullable=True)  # 나이

    # 시스템 정보
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)  # 계정 생성 일시

    # relationships
    owned_families = relationship(
        "Family",
        back_populates="owner",
        foreign_keys="Family.owner_user_id"
    )
    owned_tags = relationship("Tag", back_populates="owner")
    family_members = relationship("FamilyMember", back_populates="user")
    user_devices = relationship("UserDevice", back_populates="user")
