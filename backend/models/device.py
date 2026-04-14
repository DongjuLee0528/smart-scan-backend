"""
RFID 디바이스 모델

SmartScan 시스템에서 사용되는 UHF RFID 리더기를 나타내는 데이터베이스 모델입니다.
라즈베리파이에 연결된 RFID 리더기의 정보를 저장하고 가족 단위로 관리됩니다.
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.common.db import Base


class Device(Base):
    __tablename__ = "devices"

    # 기본 식별자
    id = Column(Integer, primary_key=True, index=True)  # 내부 디바이스 ID

    # 디바이스 정보
    serial_number = Column(String(255), unique=True, nullable=False, index=True)  # RFID 리더기 시리얼 번호 (고유)

    # 연결 정보
    family_id = Column(Integer, ForeignKey("families.id"), nullable=True, index=True)  # 연결된 가족 ID (선택적)

    # 시스템 정보
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)  # 디바이스 등록 일시

    # relationships
    family = relationship("Family", back_populates="devices")
    tags = relationship("Tag", back_populates="device")
    user_devices = relationship("UserDevice", back_populates="device")
    master_tags = relationship("MasterTag", back_populates="device")
