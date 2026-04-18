"""
알림 데이터베이스 모델

Smart Scan 시스템에서 가족 구성원 간 알림을 관리하는 데이터베이스 모델입니다.
외출/귀가 상태 변화, 시스템 이벤트, 긴급 상황 등 다양한 알림을 체계적으로 관리합니다.

비즈니스 모델:
- 발송자-수신자: 가족 구성원 간 알림 전송
- 알림 타입: 외출, 귀가, 긴급상황, 시스템 알림 등
- 전송 채널: 이메일, SMS, 푸시 알림, 카카오톡 등
- 읽음 상태: 수신자의 알림 확인 여부 추적

알림 종류:
- 외출 알림: 가족 구성원의 외출 시작 통지
- 귀가 알림: 예상 시간 내 귀가 또는 지연 통지
- 긴급 알림: 비정상적인 상황이나 보안 위협
- 시스템 알림: 디바이스 상태, 배터리, 연결 문제

데이터 흐름:
1. 이벤트 감지 (RFID 스캔, 시간 초과 등)
2. 알림 생성 (발송자, 수신자, 내용 결정)
3. 채널별 전송 (이메일, SMS 등)
4. 읽음 확인 (사용자 액션에 따른 상태 업데이트)

관계 연결:
- N:1 관계: family, sender, recipient (User)
- 가족 단위 알림 관리 및 구성원 간 커뮤니케이션
"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.common.db import Base


class Notification(Base):
    """
    알림 모델

    가족 구성원 간의 다양한 알림 정보를 저장하고 관리합니다.
    """
    __tablename__ = "notifications"

    # 기본 식별자
    id = Column(Integer, primary_key=True, index=True)  # 내부 알림 ID

    # 관계 정보
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)  # 알림이 발생한 가족 ID
    sender_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # 알림 발송자 사용자 ID
    recipient_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # 알림 수신자 사용자 ID

    # 알림 메타데이터
    type = Column(String(50), nullable=False)  # 알림 타입 (outbound, return, emergency, system)
    channel = Column(String(50), nullable=False)  # 알림 채널 (email, sms, push, kakao)
    title = Column(String(255), nullable=False)  # 알림 제목
    message = Column(String(1000), nullable=False)  # 알림 내용 메시지

    # 상태 정보
    is_read = Column(Boolean, default=False, nullable=False)  # 수신자 읽음 여부
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)  # 알림 생성 시간

    family = relationship("Family")
    sender = relationship("User", foreign_keys=[sender_user_id])
    recipient = relationship("User", foreign_keys=[recipient_user_id])
