"""
아이템(소지품) 모델

RFID 태그와 연결되는 실제 물진을 나타내는 데이터베이스 모델입니다.
사용자가 대문에서 소지하고 나가는 물건들을 추적하기 위해 등록됩니다.
"""

from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.common.db import Base


class Item(Base):
    __tablename__ = "items"

    # 기본 식별자
    id = Column(Integer, primary_key=True, index=True)  # 내부 아이템 ID

    # 아이템 기본 정보
    name = Column(String(255), nullable=False)  # 아이템 이름 (예: "지갑", "핸드폰")

    # 연결 정보
    user_device_id = Column(Integer, ForeignKey("user_devices.id"), nullable=False)  # 소유자의 디바이스 연결
    tag_uid = Column(String(255), ForeignKey("master_tags.tag_uid"), nullable=False, index=True)  # 연결된 RFID 태그 UID

    # 상태 정보
    is_active = Column(Boolean, default=True, nullable=False)  # 활성 상태 (비활성시 스캔 제외)

    # 시스템 정보
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)  # 아이템 등록 일시
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )  # 마지막 수정 일시

    # relationships
    user_device = relationship("UserDevice", back_populates="items")
    master_tag = relationship("MasterTag", back_populates="items")
    scan_logs = relationship("ScanLog", back_populates="item")
