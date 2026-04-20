"""
RFID 스캔 로그 데이터베이스 모델

RFID 리더기에서 발생한 모든 스캔 이벤트를 기록하는 데이터베이스 모델입니다.
각 스캔 이벤트는 FOUND(발견) 또는 LOST(손실) 상태로 기록됩니다.

데이터 구조:
- 스캔 이벤트: RFID 리더기가 태그를 감지한 순간의 기록
- 상태 추적: FOUND/LOST 상태로 소지품의 현재 위치 추적
- 시간 순 데이터: 대문 통과 타이밍과 순서 기록

비즈니스 로직:
- 대문 통과 감지: 사용자가 대문을 통과할 때마다 자동 스캔
- 소지품 추적: 마지막 FOUND 상태 이후 LOST 상태를 비교하여 누락 감지
- 알림 트리거: 누락된 소지품 발견 시 자동 알림 발송
- 데이터 분석: 시간대별 사용 패턴 및 통계 제공

관계 연결:
- N:1 관계: user_device, item
- 인덱스: scanned_at (시간순 조회용)
"""

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.common.db import Base


class ScanLog(Base):
    """
    RFID 스캔 로그 모델

    RFID 리더기에서 발생한 스캔 이벤트를 기록하는 로그 데이터를 나타냅니다.
    """
    __tablename__ = "scan_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_device_id = Column(Integer, ForeignKey("user_devices.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=True)
    status = Column(String(50), nullable=False)
    scanned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # relationships
    user_device = relationship("UserDevice", back_populates="scan_logs")
    item = relationship("Item", back_populates="scan_logs")