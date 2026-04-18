"""
알림 시스템 API 스키마

Smart Scan 시스템의 알림 기능을 위한 API 스키마를 정의합니다.
누락된 아이템 자동 알림과 가족 간 수동 알림을 체계적으로 관리합니다.

주요 스키마:
- NotificationType: 알림 유형 (누락 알림, 수동 알림)
- NotificationChannel: 알림 채널 (카카오톡, SMS)
- SendNotificationRequest: 알림 발송 요청
- NotificationResponse: 알림 상세 정보 응답
- NotificationListResponse: 알림 목록 응답

데이터 구조:
- 알림 유형: 자동 감지된 누락 알림 vs 사용자 수동 알림
- 발송 채널: 카카오톡, SMS 등 다양한 전송 방식
- 발송자/수신자: 가족 구성원 간 알림 관계
- 읽음 상태: 수신자의 알림 확인 여부

비즈니스 규칙:
- 가족 구성원 간에만 알림 발송 가능
- 알림 내용은 공백 제거 후 필수 검증
- 읽음 상태는 수신자만 변경 가능
- 알림 이력은 가족 내에서만 공유

사용 시나리오:
- 누락된 아이템 자동 감지 시 알림 발송
- 가족 구성원 간 수동 메시지 전송
- 알림 목록 조회 및 읽음 처리
- 알림 발송 이력 관리 및 추적
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator


class NotificationType(str, Enum):
    """
    알림 유형 열거형

    알림의 발생 원인과 처리 방식을 구분합니다.
    """
    MISSING_ALERT = "missing_alert"  # 누락 아이템 자동 감지 알림
    MANUAL_ALERT = "manual_alert"  # 사용자 수동 발송 알림


class NotificationChannel(str, Enum):
    """
    알림 채널 열거형

    알림을 전송할 수 있는 다양한 채널을 정의합니다.
    """
    KAKAO = "kakao"  # 카카오톡 알림
    SMS = "sms"  # SMS 문자 메시지


def _validate_required_text(value: str, field_name: str) -> str:
    """
    필수 텍스트 필드 검증

    공백 제거 후 빈 값 체크를 수행합니다.

    Args:
        value: 검증할 텍스트 값
        field_name: 필드명 (오류 메시지용)

    Returns:
        str: 정규화된 텍스트

    Raises:
        ValueError: 빈 값일 경우
    """
    normalized_value = value.strip()
    if not normalized_value:
        raise ValueError(f"{field_name} is required")
    return normalized_value


class SendNotificationRequest(BaseModel):
    """
    알림 발송 요청 스키마

    가족 구성원이 다른 구성원에게 알림을 발송할 때 사용됩니다.
    """
    channel: NotificationChannel  # 알림 발송 채널
    title: str  # 알림 제목
    message: str  # 알림 내용

    @field_validator("title", "message")
    @classmethod
    def validate_required_text(cls, v: str, info) -> str:
        """제목과 메시지 필수 검증"""
        return _validate_required_text(v, info.field_name)


class NotificationResponse(BaseModel):
    """
    알림 상세 정보 응답 스키마

    개별 알림의 모든 정보를 클라이언트에 전달합니다.
    """
    id: int  # 알림 고유 ID
    family_id: int  # 가족 ID
    sender_user_id: int  # 발송자 사용자 ID
    recipient_user_id: int  # 수신자 사용자 ID
    type: NotificationType  # 알림 유형
    channel: NotificationChannel  # 발송 채널
    title: str  # 알림 제목
    message: str  # 알림 내용
    is_read: bool  # 읽음 여부
    created_at: datetime  # 생성 시간

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    """
    알림 목록 응답 스키마

    사용자의 알림 목록과 총 개수 정보를 함께 제공합니다.
    """
    notifications: list[NotificationResponse]  # 알림 목록
    total_count: int  # 총 알림 개수
