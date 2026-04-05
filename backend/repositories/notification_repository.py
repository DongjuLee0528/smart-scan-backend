from typing import Optional

from sqlalchemy.orm import Session

from backend.models.notification import Notification


class NotificationRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_by_id(self, notification_id: int) -> Optional[Notification]:
        return self.db.query(Notification).filter(Notification.id == notification_id).first()

    def find_all_by_recipient_user_id(self, recipient_user_id: int) -> list[Notification]:
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
        notification = Notification(
            family_id=family_id,
            sender_user_id=sender_user_id,
            recipient_user_id=recipient_user_id,
            type=notification_type,
            channel=channel,
            title=title,
            message=message,
            is_read=False
        )
        self.db.add(notification)
        self.db.flush()
        return notification

    def mark_as_read(self, notification: Notification) -> Notification:
        notification.is_read = True
        self.db.flush()
        return notification
