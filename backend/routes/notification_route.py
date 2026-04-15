"""
알림 관리 API 라우터

SmartScan 시스템의 알림 기능을 위한 API 엔드포인트를 제공합니다.
가족 구성원 간 수동 알림 전송과 알림 이력 조회 기능을 지원합니다.

주요 엔드포인트:
- POST /send: 가족 구성원에게 수동 알림 전송
- GET /: 알림 이력 조회 (가족 단위)
- GET /{notification_id}: 특정 알림 상세 조회

알림 기능:
- 수동 알림: 가족 구성원에게 커스텀 메시지 전송
- 자동 알림: RFID 스캔 결과 기반 누락 아이템 알림 (별도 Lambda 처리)
- 알림 이력: 발송된 모든 알림의 기록과 상태 추적

지원 채널:
- 이메일: 기본 알림 채널
- 카카오톡: 향후 확장 예정
- 푸시 알림: 향후 확장 예정

비즈니스 규칙:
- 가족 구성원만 서로에게 알림 전송 가능
- Rate limiting으로 스팸 방지
- 알림 내용 길이 제한 (보안 및 성능)
- 발송 실패 시 재시도 로직

보안: JWT 인증 필요, 가족 단위 권한 격리
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.common.dependencies import get_current_user
from backend.common.db import get_db
from backend.common.response import success_response
from backend.common.route_decorators import handle_service_errors, validate_positive_id, validate_required_string
from backend.common.rate_limiter import limiter, api_rate_limit
from backend.schemas.notification_schema import SendNotificationRequest
from backend.services.notification_service import NotificationService


router = APIRouter(tags=["notifications"])


def get_notification_service(db: Session = Depends(get_db)) -> NotificationService:
    return NotificationService(db)


@router.post("/send/{user_id}", response_model=dict)
@limiter.limit(api_rate_limit)
@handle_service_errors
def send_notification(
    user_id: int,
    request: SendNotificationRequest,
    http_request: Request,
    current_user=Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    validate_positive_id("user_id", user_id)
    validate_required_string("title", request.title)
    validate_required_string("message", request.message)

    result = notification_service.send_manual_notification(
        user_id=current_user.id,
        recipient_user_id=user_id,
        channel=request.channel,
        title=request.title,
        message=request.message
    )
    return success_response("Notification sent successfully", result.model_dump())


@router.get("", response_model=dict)
@handle_service_errors
def get_my_notifications(
    current_user=Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    result = notification_service.get_my_notifications(current_user.id)
    return success_response("Notifications retrieved successfully", result.model_dump())


@router.patch("/{notification_id}/read", response_model=dict)
@handle_service_errors
def mark_notification_as_read(
    notification_id: int,
    current_user=Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    validate_positive_id("notification_id", notification_id)

    result = notification_service.mark_as_read(
        user_id=current_user.id,
        notification_id=notification_id
    )
    return success_response("Notification marked as read successfully", result.model_dump())
