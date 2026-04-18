"""
마스터 태그 데이터베이스 모델

실제 물리적 RFID 태그를 나타내는 데이터베이스 모델입니다.
RFID 리더기에 연결된 실제 태그들을 대표하며, 나중에 아이템과 연결됩니다.

비즈니스 모델:
- 물리적 태그: 실제로 존재하는 RFID 태그 하드웨어
- 디바이스 종속: 특정 RFID 리더기 디바이스에 부착된 태그
- 라벨 시스템: label_id를 통한 카테고리 분류 지원
- 아이템 연결 대기: 아직 아이템과 연결되지 않은 태그

데이터 무결성:
- tag_uid 고유성: 전체 시스템에서 유일한 식별자
- 디바이스 연결: 특정 RFID 리더기에만 연결된 태그
- 라벨 기반 분류: 비즈니스 로직에서 태그 그룹핑에 사용

관계 연결:
- N:1 관계: device
- 1:N 관계: items (태그당 여러 아이템 연결 가능)
"""

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from backend.common.db import Base


class MasterTag(Base):
    """
    마스터 태그 모델

    실제 물리적 RFID 태그 하드웨어를 나타내는 데이터 모델입니다.
    """
    __tablename__ = "master_tags"

    id = Column(Integer, primary_key=True, index=True)
    tag_uid = Column(String(255), unique=True, nullable=False, index=True)
    label_id = Column(Integer, nullable=False, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)

    # relationships
    device = relationship("Device", back_populates="master_tags")
    items = relationship("Item", back_populates="master_tag")
