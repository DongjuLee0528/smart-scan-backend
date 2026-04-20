"""
가족 초대 데이터 접근 계층

family_invitations 테이블에 대한 CRUD 및 조회 로직을 제공합니다.
서비스 레이어에서 상태 전환(pending → accepted/declined/cancelled/expired)에
필요한 쿼리를 담당합니다.

주요 쿼리 패턴:
- 토큰으로 단일 초대 조회 (공개 수락/거절 플로우)
- (family_id, email, status=pending)으로 중복 초대 확인
- family_id + pending 상태로 목록 조회 (오너 대시보드)
- expires_at 기반 만료 필터링
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from backend.models.family_invitation import FamilyInvitation


class FamilyInvitationRepository:
    """
    가족 초대 데이터 접근 클래스

    family_invitations 테이블에 대한 CRUD와 상태 관리 메서드를 제공한다.
    """

    def __init__(self, db: Session):
        """데이터베이스 세션 주입"""
        self.db = db

    def find_by_token(self, token: UUID) -> Optional[FamilyInvitation]:
        """
        UUID 토큰으로 초대 조회 (family, inviter 조인 포함)

        Args:
            token: 초대 링크에 포함된 UUID

        Returns:
            FamilyInvitation | None: 일치하는 초대 레코드 또는 None
        """
        return (
            self.db.query(FamilyInvitation)
            .options(
                joinedload(FamilyInvitation.family),
                joinedload(FamilyInvitation.inviter),
            )
            .filter(FamilyInvitation.token == token)
            .first()
        )

    def find_by_id(self, invitation_id: int) -> Optional[FamilyInvitation]:
        """
        초대 ID로 조회 (family, inviter 조인 포함)

        Args:
            invitation_id: 초대 고유 ID

        Returns:
            FamilyInvitation | None
        """
        return (
            self.db.query(FamilyInvitation)
            .options(
                joinedload(FamilyInvitation.family),
                joinedload(FamilyInvitation.inviter),
            )
            .filter(FamilyInvitation.id == invitation_id)
            .first()
        )

    def find_pending_by_family_and_email(
        self, family_id: int, email: str
    ) -> Optional[FamilyInvitation]:
        """
        (family_id, email) 조합으로 pending 초대 존재 여부 확인

        중복 초대 방지를 위해 사용한다.

        Args:
            family_id: 가족 ID
            email: 초대 대상 이메일 (소문자 정규화 후 전달)

        Returns:
            FamilyInvitation | None: pending 상태의 초대 또는 None
        """
        return (
            self.db.query(FamilyInvitation)
            .filter(
                FamilyInvitation.family_id == family_id,
                FamilyInvitation.email == email,
                FamilyInvitation.status == "pending",
                FamilyInvitation.expires_at > datetime.now(timezone.utc),
            )
            .first()
        )

    def find_pending_by_family_id(self, family_id: int) -> list[FamilyInvitation]:
        """
        family_id 기준 pending 초대 목록 조회 (만료 미포함)

        오너 대시보드에서 진행 중인 초대 목록을 보여줄 때 사용한다.

        Args:
            family_id: 가족 ID

        Returns:
            list[FamilyInvitation]: pending + 미만료 초대 목록 (생성일 내림차순)
        """
        return (
            self.db.query(FamilyInvitation)
            .options(joinedload(FamilyInvitation.inviter))
            .filter(
                FamilyInvitation.family_id == family_id,
                FamilyInvitation.status == "pending",
                FamilyInvitation.expires_at > datetime.now(timezone.utc),
            )
            .order_by(FamilyInvitation.created_at.desc())
            .all()
        )

    def create(
        self,
        family_id: int,
        inviter_user_id: int,
        email: str,
        suggested_name: Optional[str],
        suggested_phone: Optional[str],
        suggested_age: Optional[int],
        expires_at: datetime,
    ) -> FamilyInvitation:
        """
        새 초대 레코드 생성 (token은 모델 기본값으로 자동 생성)

        Args:
            family_id: 초대할 가족 ID
            inviter_user_id: 초대를 발송하는 사용자 ID
            email: 초대 대상 이메일 (소문자 정규화 후 전달)
            suggested_name: 관리자가 제안하는 이름 (참고용)
            suggested_phone: 제안 전화번호
            suggested_age: 제안 나이
            expires_at: 만료 시각 (UTC)

        Returns:
            FamilyInvitation: 생성된 초대 레코드 (flush 완료)
        """
        invitation = FamilyInvitation(
            family_id=family_id,
            inviter_user_id=inviter_user_id,
            email=email,
            suggested_name=suggested_name,
            suggested_phone=suggested_phone,
            suggested_age=suggested_age,
            expires_at=expires_at,
        )
        self.db.add(invitation)
        self.db.flush()
        return invitation

    def update_status(
        self,
        invitation: FamilyInvitation,
        status: str,
        timestamp_field: Optional[str] = None,
        timestamp_value: Optional[datetime] = None,
    ) -> FamilyInvitation:
        """
        초대 상태 업데이트

        Args:
            invitation: 업데이트할 초대 엔티티
            status: 새 상태 값 (accepted / declined / cancelled / expired)
            timestamp_field: 설정할 타임스탬프 컬럼명 (예: 'accepted_at')
            timestamp_value: 설정할 시각 값

        Returns:
            FamilyInvitation: 업데이트된 엔티티 (flush 완료)
        """
        invitation.status = status
        if timestamp_field and timestamp_value:
            setattr(invitation, timestamp_field, timestamp_value)
        self.db.flush()
        return invitation
