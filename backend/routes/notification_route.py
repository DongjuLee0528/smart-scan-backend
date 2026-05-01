"""
Notification management API router

Provides API endpoints for notification features in SmartScan system.
Supports manual notification sending between family members and notification history lookup.

Main endpoints:
- POST /send: Send manual notification to family members
- GET /: Notification history lookup (family unit)
- GET /{notification_id}: Specific notification detail lookup

Notification features:
- Manual notifications: Send custom messages to family members
- Automatic notifications: Missing item alerts based on RFID scan results (handled by separate Lambda)
- Notification history: Record and status tracking of all sent notifications

Supported channels:
- Email: Default notification channel
- KakaoTalk: Future expansion planned
- Push notifications: Future expansion planned

Business rules:
- Only family members can send notifications to each other
- Spam prevention through rate limiting
- Notification content length restrictions (security and performance)
- Retry logic when sending fails

Security: JWT authentication required, family-unit permission isolation
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
    request: Request,
    user_id: int,
    payload: SendNotificationRequest,
    current_user=Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    validate_positive_id("user_id", user_id)
    validate_required_string("title", payload.title)
    validate_required_string("message", payload.message)

    result = notification_service.send_manual_notification(
        user_id=current_user.id,
        recipient_user_id=user_id,
        channel=payload.channel,
        title=payload.title,
        message=payload.message
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
