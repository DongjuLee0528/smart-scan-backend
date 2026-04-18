"""
알림 데이터 접근 계층

SmartScan 시스템의 알림 기능을 위한 데이터베이스 작업을 담당하는 리포지토리입니다.
누락 아이템 자동 알림, 가족 간 수동 알림 등 모든 알림 데이터를 관리합니다.

데이터 관리:
- 알림 생성, 조회, 상태 업데이트
- 수신자별 알림 목록 관리
- 알림 유형별 분류 (자동/수동, 이메일/푸시 등)
- 알림 발송 이력 및 실패 로그 추적

비즈니스 규칙:
- 가족 구성원은 서로의 알림 이력 조회 가능
- 알림 발송 실패 시 재시도 로직 지원
- 개인정보 보호를 위한 알림 내용 암호화 옵션
- 스팸 방지를 위한 빈도 제한 데이터 관리

주요 쿼리 패턴:
- 사용자별 알림 목록 조회 (최신순)
- 미읽음 알림 카운트
- 알림 유형별 필터링
- 발송 실패 알림 재시도 대상 조회
"""

from typing import Optional

from sqlalchemy.orm import Session

from backend.models.notification import Notification


class NotificationRepository:
    """
    알림 데이터 접근 클래스

    알림 테이블에 대한 CRUD 작업과 알림 관리 비즈니스 로직을 제공합니다.
    """
    def __init__(self, db: Session):
        self.db = db

    def find_by_id(self, notification_id: int) -> Optional[Notification]:
        """
        알림 ID로 알림 조회

        Args:
            notification_id: 조회할 알림의 고유 ID

        Returns:
            Optional[Notification]: 일치하는 알림 또는 None
        """
        return self.db.query(Notification).filter(Notification.id == notification_id).first()

    def find_all_by_recipient_user_id(self, recipient_user_id: int) -> list[Notification]:
        """
        수신자 사용자 ID로 모든 알림 조회

        사용자의 알림 목록을 최신순으로 조회합니다.

        Args:
            recipient_user_id: 수신자 사용자 ID

        Returns:
            list[Notification]: 수신자의 모든 알림 목록 (최신순)
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
        새 알림 생성

        Args:
            family_id: 알림이 발생한 가족 ID
            sender_user_id: 알림 발송자 사용자 ID
            recipient_user_id: 알림 수신자 사용자 ID
            notification_type: 알림 타입 (outbound, return, emergency, system)
            channel: 알림 채널 (email, sms, push, kakao)
            title: 알림 제목
            message: 알림 내용 메시지

        Returns:
            Notification: 생성된 알림 엔티티
        """
        notification = Notification(
            family_id=family_id,
            sender_user_id=sender_user_id,
            recipient_user_id=recipient_user_id,
            type=notification_type,
            channel=channel,
            title=title,
            message=message,
            is_read=False  # 새 알림은 미읽음 상태로 생성
        )
        self.db.add(notification)
        self.db.flush()
        return notification

    def mark_as_read(self, notification: Notification) -> Notification:
        """
        알림을 읽음 상태로 표시

        Args:
            notification: 읽음 처리할 알림 엔티티

        Returns:
            Notification: 업데이트된 알림 엔티티
        """
        notification.is_read = True
        self.db.flush()
        return notification
