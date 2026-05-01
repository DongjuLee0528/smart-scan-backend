"""
Notification system API schemas

Defines API schemas for notification functionality in Smart Scan system.
Systematically manages automatic missing item alerts and manual alerts between family members.

Main schemas:
- NotificationType: Notification type (missing alert, manual alert)
- NotificationChannel: Notification channel (KakaoTalk, SMS)
- SendNotificationRequest: Notification sending request
- NotificationResponse: Notification detail information response
- NotificationListResponse: Notification list response

Data structure:
- Notification type: Automatically detected missing alert vs user manual alert
- Sending channel: Various transmission methods like KakaoTalk, SMS, etc.
- Sender/recipient: Notification relationship between family members
- Read status: Whether recipient has confirmed notification

Business rules:
- Notifications can only be sent between family members
- Notification content is validated as required after removing whitespace
- Read status can only be changed by recipient
- Notification history is shared only within family

Usage scenarios:
- Send notifications when missing items are automatically detected
- Manual message transmission between family members
- Query notification list and process read status
- Manage and track notification sending history
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator


class NotificationType(str, Enum):
    """
    Notification type enumeration

    Distinguishes notification cause and processing method.
    """
    MISSING_ALERT = "missing_alert"  # Missing item automatic detection alert
    MANUAL_ALERT = "manual_alert"  # User manual sending alert


class NotificationChannel(str, Enum):
    """
    Notification channel enumeration

    Defines various channels through which notifications can be sent.
    """
    KAKAO = "kakao"  # KakaoTalk notification
    SMS = "sms"  # SMS text message
    EMAIL = "email"  # Email notification


def _validate_required_text(value: str, field_name: str) -> str:
    """
    Required text field validation

    Performs empty value check after removing whitespace.

    Args:
        value: Text value to validate
        field_name: Field name (for error message)

    Returns:
        str: Normalized text

    Raises:
        ValueError: When value is empty
    """
    normalized_value = value.strip()
    if not normalized_value:
        raise ValueError(f"{field_name} is required")
    return normalized_value


class SendNotificationRequest(BaseModel):
    """
    Notification sending request schema

    Used when family member sends notification to other member.
    """
    channel: NotificationChannel  # Notification sending channel
    title: str  # Notification title
    message: str  # Notification content

    @field_validator("title", "message")
    @classmethod
    def validate_required_text(cls, v: str, info) -> str:
        """Required validation for title and message"""
        return _validate_required_text(v, info.field_name)


class NotificationResponse(BaseModel):
    """
    Notification detail information response schema

    Delivers all information of individual notification to client.
    """
    id: int  # Notification unique ID
    family_id: int  # Family ID
    sender_user_id: int  # Sender user ID
    recipient_user_id: int  # Recipient user ID
    type: NotificationType  # Notification type
    channel: NotificationChannel  # Sending channel
    title: str  # Notification title
    message: str  # Notification content
    is_read: bool  # Read status
    created_at: datetime  # Creation time

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    """
    Notification list response schema

    Provides user's notification list together with total count information.
    """
    notifications: list[NotificationResponse]  # Notification list
    total_count: int  # Total notification count
