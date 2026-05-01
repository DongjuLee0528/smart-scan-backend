"""
Notification data access layer

Repository responsible for database operations for notification features in SmartScan system.
Manages all notification data including automatic missing item alerts, manual family notifications, etc.

Data management:
- Notification creation, lookup, status updates
- Notification list management by recipient
- Classification by notification type (auto/manual, email/push, etc.)
- Notification sending history and failure log tracking

Business rules:
- Family members can view each other's notification history
- Support retry logic for notification sending failures
- Notification content encryption options for privacy protection
- Frequency limit data management for spam prevention

Main query patterns:
- User notification list lookup (latest first)
- Unread notification count
- Filtering by notification type
- Retry target lookup for failed notifications
"""

from typing import Optional

from sqlalchemy.orm import Session

from backend.models.notification import Notification


class NotificationRepository:
    """
    Notification data access class

    Provides CRUD operations for notification table and notification management business logic.
    """
    def __init__(self, db: Session):
        self.db = db

    def find_by_id(self, notification_id: int) -> Optional[Notification]:
        """
        Find notification by notification ID

        Args:
            notification_id: Unique ID of notification to find

        Returns:
            Optional[Notification]: Matching notification or None
        """
        return self.db.query(Notification).filter(Notification.id == notification_id).first()

    def find_all_by_recipient_user_id(self, recipient_user_id: int) -> list[Notification]:
        """
        Find all notifications by recipient user ID

        Query user's notification list in latest order.

        Args:
            recipient_user_id: Recipient user ID

        Returns:
            list[Notification]: All notification list of recipient (latest order)
        """
        return self.db.query(Notification).filter(
            Notification.recipient_user_id == recipient_user_id
        ).order_by(Notification.created_at.desc(), Notification.id.desc()).all()

    def create(
        self,
        family_id: int,
        sender_user_id: int,
        recipient_user_id: int,
        notification_type: str,
        channel: str,
        title: str,
        message: str
    ) -> Notification:
        """
        Create new notification

        Args:
            family_id: Family ID where notification occurred
            sender_user_id: Notification sender user ID
            recipient_user_id: Notification recipient user ID
            notification_type: Notification type (outbound, return, emergency, system)
            channel: Notification channel (email, sms, push, kakao)
            title: Notification title
            message: Notification content message

        Returns:
            Notification: Created notification entity
        """
        notification = Notification(
            family_id=family_id,
            sender_user_id=sender_user_id,
            recipient_user_id=recipient_user_id,
            type=notification_type,
            channel=channel,
            title=title,
            message=message,
            is_read=False  # New notifications are created as unread
        )
        self.db.add(notification)
        self.db.flush()
        return notification

    def mark_as_read(self, notification: Notification) -> Notification:
        """
        Mark notification as read

        Args:
            notification: Notification entity to mark as read

        Returns:
            Notification: Updated notification entity
        """
        notification.is_read = True
        self.db.flush()
        return notification
