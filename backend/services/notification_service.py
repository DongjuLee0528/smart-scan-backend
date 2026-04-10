from sqlalchemy.orm import Session

from backend.common.exceptions import BadRequestException, ForbiddenException, NotFoundException
from backend.common.service_base import ServiceBase
from backend.common.validator import validate_non_empty_string, validate_positive_int
from backend.repositories.family_member_repository import FamilyMemberRepository
from backend.repositories.family_repository import FamilyRepository
from backend.repositories.notification_repository import NotificationRepository
from backend.repositories.user_repository import UserRepository
from backend.schemas.monitoring_schema import TagCurrentStatus
from backend.schemas.notification_schema import (
    NotificationChannel,
    NotificationListResponse,
    NotificationResponse,
    NotificationType,
)
from backend.services.monitoring_service import MonitoringService


class NotificationService(ServiceBase):
    def __init__(self, db: Session):
        super().__init__(db)
        self.notification_repository = NotificationRepository(db)
        self.monitoring_service = MonitoringService(db)

    def send_manual_notification(
        self,
        user_id: int,
        recipient_user_id: int,
        channel: NotificationChannel,
        title: str,
        message: str
    ) -> NotificationResponse:
        validate_positive_int(user_id, "user_id")
        validate_positive_int(recipient_user_id, "recipient_user_id")
        validate_non_empty_string(title, "title")
        validate_non_empty_string(message, "message")

        # 발신자 권한 및 가족 컨텍스트 확인
        actor, actor_family_member, family = self._get_actor_context(user_id)
        self._ensure_family_owner(actor.id, actor_family_member.role, family.owner_user_id)

        # 수신자가 발신자와 동일한 가족에 속하는지 확인
        recipient_member = self._get_family_member_or_raise(family.id, recipient_user_id)

        try:
            notification = self.notification_repository.create(
                family_id=family.id,
                sender_user_id=actor.id,
                recipient_user_id=recipient_member.user_id,
                notification_type=NotificationType.MANUAL_ALERT.value,
                channel=channel.value,
                title=title.strip(),
                message=message.strip()
            )
            self.db.commit()
            self.db.refresh(notification)
            self._dispatch_notification(notification)
            return self._build_notification_response(notification)
        except Exception:
            self.db.rollback()
            raise

    def get_my_notifications(self, user_id: int) -> NotificationListResponse:
        validate_positive_int(user_id, "user_id")
        actor, _, _ = self._get_actor_context(user_id)
        notifications = self.notification_repository.find_all_by_recipient_user_id(actor.id)
        return NotificationListResponse(
            notifications=[self._build_notification_response(notification) for notification in notifications],
            total_count=len(notifications)
        )

    def mark_as_read(self, user_id: int, notification_id: int) -> NotificationResponse:
        validate_positive_int(user_id, "user_id")
        validate_positive_int(notification_id, "id")

        actor, _, family = self._get_actor_context(user_id)
        notification = self.notification_repository.find_by_id(notification_id)
        if not notification:
            raise NotFoundException("Notification not found")

        if notification.family_id != family.id or notification.recipient_user_id != actor.id:
            raise ForbiddenException("Notification is not accessible")

        try:
            updated_notification = self.notification_repository.mark_as_read(notification)
            self.db.commit()
            self.db.refresh(updated_notification)
            return self._build_notification_response(updated_notification)
        except Exception:
            self.db.rollback()
            raise

    def record_missing_alerts(
        self,
        user_id: int,
        recipient_user_id: int | None = None,
        channel: NotificationChannel = NotificationChannel.KAKAO
    ) -> NotificationListResponse:
        validate_positive_int(user_id, "user_id")
        actor, _, family = self._get_actor_context(user_id)
        target_user_id = recipient_user_id or actor.id
        recipient_member = self._get_family_member_or_raise(family.id, target_user_id)
        member_tags = self.monitoring_service.get_member_tags(user_id, recipient_member.id)
        lost_tags = [tag for tag in member_tags.tags if tag.status == TagCurrentStatus.LOST]

        created_notifications = []
        try:
            for lost_tag in lost_tags:
                notification = self.notification_repository.create(
                    family_id=family.id,
                    sender_user_id=family.owner_user_id,
                    recipient_user_id=recipient_member.user_id,
                    notification_type=NotificationType.MISSING_ALERT.value,
                    channel=channel.value,
                    title=self._build_missing_alert_title(lost_tag.name),
                    message=self._build_missing_alert_message(lost_tag.name, lost_tag.last_seen_at)
                )
                created_notifications.append(notification)

            self.db.commit()
            for notification in created_notifications:
                self.db.refresh(notification)
                self._dispatch_notification(notification)

            return NotificationListResponse(
                notifications=[self._build_notification_response(notification) for notification in created_notifications],
                total_count=len(created_notifications)
            )
        except Exception:
            self.db.rollback()
            raise


    def _get_family_member_or_raise(self, family_id: int, user_id: int):
        family_member = self.family_member_repository.find_by_family_id_and_user_id(family_id, user_id)
        if not family_member:
            raise ForbiddenException("Recipient is not accessible in this family")
        return family_member

    @staticmethod
    def _ensure_family_owner(actor_user_id: int, role: str, owner_user_id: int) -> None:
        if role != "owner" or actor_user_id != owner_user_id:
            raise ForbiddenException("Only family owner can send manual notifications")

    @staticmethod
    def _build_missing_alert_title(tag_name: str) -> str:
        return f"누락 감지 알림: {tag_name}"

    @staticmethod
    def _build_missing_alert_message(tag_name: str, last_seen_at) -> str:
        if last_seen_at is None:
            return f"{tag_name} 태그가 누락 상태로 감지되었습니다."
        return f"{tag_name} 태그가 누락 상태로 감지되었습니다. 마지막 감지 시각: {last_seen_at.isoformat()}"

    @staticmethod
    def _build_notification_response(notification) -> NotificationResponse:
        return NotificationResponse(
            id=notification.id,
            family_id=notification.family_id,
            sender_user_id=notification.sender_user_id,
            recipient_user_id=notification.recipient_user_id,
            type=NotificationType(notification.type),
            channel=NotificationChannel(notification.channel),
            title=notification.title,
            message=notification.message,
            is_read=notification.is_read,
            created_at=notification.created_at
        )

    @staticmethod
    def _dispatch_notification(notification) -> None:
        _ = notification
