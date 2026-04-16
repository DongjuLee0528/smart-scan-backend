"""
RFID 디바이스 데이터베이스 모델

Smart Scan 시스템의 UHF RFID 리더기 디바이스를 관리하는 데이터베이스 모델입니다.
라즈베리파이에 연결된 RFID 리더기의 등록, 관리, 가족 연결 정보를 저장합니다.

비즈니스 모델:
- 디바이스 등록: 시리얼 번호 기반 고유 디바이스 식별
- 가족 연결: 가족 단위 디바이스 소유권 관리
- 태그 연결: 디바이스에 등록된 RFID 태그들과의 관계

디바이스 생명주기:
1. 등록 (created_at): 새 디바이스의 시리얼 번호 등록
2. 할당 (family_id): 특정 가족에게 디바이스 소유권 부여
3. 사용: RFID 태그 스캔 및 아이템 추적
4. 해제: 가족 연결 해제 및 재할당 대기

하드웨어 구성:
- 라즈베리파이 + UHF RFID 리더기 모듈
- 고유 시리얼 번호를 통한 디바이스 식별
- 네트워크 연결을 통한 클라우드 통신

관계 연결:
- N:1 관계: family (디바이스가 소속된 가족)
- 1:N 관계: tags (디바이스에 등록된 태그들)
- 1:N 관계: master_tags (디바이스별 마스터 태그들)
- 1:N 관계: user_devices (사용자별 디바이스 접근 권한)
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.common.db import Base


class Device(Base):
    """
    RFID 디바이스 모델

    UHF RFID 리더기 디바이스의 정보를 저장하고 관리합니다.
    """
    __tablename__ = "devices"

    # 기본 식별자
    id = Column(Integer, primary_key=True, index=True)  # 내부 디바이스 ID

    # 디바이스 정보
    serial_number = Column(String(255), unique=True, nullable=False, index=True)  # RFID 리더기 시리얼 번호 (고유)

    # 연결 정보
    family_id = Column(Integer, ForeignKey("families.id"), nullable=True, index=True)  # 연결된 가족 ID (선택적)

    # 시스템 정보
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)  # 디바이스 등록 일시

    # 관계 정의
    family = relationship("Family", back_populates="devices")  # 디바이스가 소속된 가족
    tags = relationship("Tag", back_populates="device")  # 디바이스에 등록된 태그들
    user_devices = relationship("UserDevice", back_populates="device")  # 사용자별 디바이스 접근 권한
    master_tags = relationship("MasterTag", back_populates="device")  # 디바이스별 마스터 태그들
