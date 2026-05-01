"""
Family invitation service

Handles entire invitation flow including family invitation creation, lookup, acceptance, rejection, and cancellation.

Main features:
- Invitation creation and email sending (atomic processing, rollback on email failure)
- Token-based public invitation information lookup (includes lazy expire processing)
- Invitation acceptance: Leave existing family_member + join new family + device connection
- Invitation rejection/cancellation: Status transition only

Business rules:
- Only family owners can send/cancel invitations
- When accepting invitation, delete family itself if current family has only the user
- Cannot accept if owner of another family with members other than self
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from backend.common.exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from backend.common.service_base import ServiceBase
from backend.repositories.device_repository import DeviceRepository
from backend.repositories.family_invitation_repository import FamilyInvitationRepository
from backend.repositories.user_device_repository import UserDeviceRepository
from backend.schemas.family_invitation_schema import (
    AcceptInvitationResponse,
    DeclineInvitationResponse,
    InvitationListResponse,
    InvitationResponse,
)
from backend.services.email_service import EmailService

_INVITATION_EXPIRE_DAYS = 7


class FamilyInvitationService(ServiceBase):
    """
    가족 초대 서비스 클래스

    ServiceBase를 상속하여 actor context 조회, 공통 레포지토리를 활용한다.
    """

    def __init__(self, db: Session):
        super().__init__(db)
        self.invitation_repository = FamilyInvitationRepository(db)
        self.device_repository = DeviceRepository(db)
        self.user_device_repository = UserDeviceRepository(db)
        self.email_service = EmailService()

    # ------------------------------------------------------------------
    # 1. 초대 생성
    # ------------------------------------------------------------------

    def create_invitation(
        self,
        actor_user_id: int,
        name: str,
        email: str,
        phone_number: str,
        age: int | None,
    ) -> InvitationResponse:
        """
        가족 초대 생성 및 이메일 발송

        이메일 발송 실패 시 rollback하여 데이터 정합성을 보장한다.

        Args:
            actor_user_id: 초대를 발송하는 유저 ID (family owner여야 함)
            name: 초대 대상 이름 (참고용)
            email: 초대 대상 이메일
            phone_number: 초대 대상 전화번호 (참고용)
            age: 초대 대상 나이 (참고용, nullable)

        Returns:
            InvitationResponse: 생성된 초대 정보

        Raises:
            ForbiddenException: actor가 family owner가 아닌 경우
            BadRequestException: 자기 자신을 초대하려는 경우
            ConflictException: 동일 (family, email) pending 초대 이미 존재 또는 이미 멤버인 경우
        """
        actor, actor_family_member, family = self._get_actor_context(actor_user_id)
        _ensure_owner(actor.id, actor_family_member.role, family.owner_user_id)

        normalized_email = email.strip().lower()

        # 자기 자신 초대 방지
        if actor.email and actor.email.strip().lower() == normalized_email:
            raise BadRequestException("Cannot invite yourself")

        # pending 초대 중복 확인
        existing_invitation = self.invitation_repository.find_pending_by_family_and_email(
            family.id, normalized_email
        )
        if existing_invitation:
            raise ConflictException("An active invitation already exists for this email")

        # 이미 해당 family member인 경우 확인
        target_user = self.user_repository.find_by_email(normalized_email)
        if target_user:
            existing_member = self.family_member_repository.find_by_family_id_and_user_id(
                family.id, target_user.id
            )
            if existing_member:
                raise ConflictException("User is already a member of this family")

        expires_at = datetime.now(timezone.utc) + timedelta(days=_INVITATION_EXPIRE_DAYS)

        try:
            invitation = self.invitation_repository.create(
                family_id=family.id,
                inviter_user_id=actor.id,
                email=normalized_email,
                suggested_name=name.strip() if name else None,
                suggested_phone=phone_number.strip() if phone_number else None,
                suggested_age=age,
                expires_at=expires_at,
            )
            # flush 후 token이 확정된 상태에서 이메일 발송 — 실패 시 예외가 전파되어 rollback
            self.email_service.send_invitation_email(
                to_email=normalized_email,
                inviter_name=actor.name or actor.email,
                family_name=family.family_name,
                token=str(invitation.token),
                expires_at=expires_at,
            )
            self.db.commit()
            # commit 이후 relationships 재로드
            self.db.refresh(invitation)
            return _build_invitation_response(invitation, family.family_name, actor.name or actor.email)
        except Exception:
            self.db.rollback()
            raise

    # ------------------------------------------------------------------
    # 2. 초대 목록 조회 (owner)
    # ------------------------------------------------------------------

    def list_invitations(self, actor_user_id: int) -> InvitationListResponse:
        """
        현재 family의 pending 초대 목록 조회 (만료된 항목 제외)

        Args:
            actor_user_id: 조회를 요청한 유저 ID (family owner여야 함)

        Returns:
            InvitationListResponse
        """
        actor, actor_family_member, family = self._get_actor_context(actor_user_id)
        _ensure_owner(actor.id, actor_family_member.role, family.owner_user_id)

        invitations = self.invitation_repository.find_pending_by_family_id(family.id)
        responses = [
            _build_invitation_response(
                inv,
                family.family_name,
                inv.inviter.name or inv.inviter.email if inv.inviter else "",
            )
            for inv in invitations
        ]
        return InvitationListResponse(invitations=responses, total_count=len(responses))

    # ------------------------------------------------------------------
    # 3. 초대 취소
    # ------------------------------------------------------------------

    def cancel_invitation(self, actor_user_id: int, invitation_id: int) -> bool:
        """
        초대 취소 (status: pending → cancelled)

        Args:
            actor_user_id: 취소를 요청한 유저 ID (family owner여야 함)
            invitation_id: 취소할 초대 ID

        Returns:
            True

        Raises:
            NotFoundException: 초대를 찾을 수 없는 경우
            ForbiddenException: 해당 family의 초대가 아닌 경우
            BadRequestException: 이미 pending이 아닌 경우
        """
        actor, actor_family_member, family = self._get_actor_context(actor_user_id)
        _ensure_owner(actor.id, actor_family_member.role, family.owner_user_id)

        invitation = self.invitation_repository.find_by_id(invitation_id)
        if not invitation:
            raise NotFoundException("Invitation not found")

        if invitation.family_id != family.id:
            raise ForbiddenException("Invitation does not belong to your family")

        if invitation.status != "pending":
            raise BadRequestException(f"Invitation is already {invitation.status}")

        try:
            self.invitation_repository.update_status(
                invitation,
                status="cancelled",
                timestamp_field="cancelled_at",
                timestamp_value=datetime.now(timezone.utc),
            )
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise

    # ------------------------------------------------------------------
    # 4. 토큰으로 초대 정보 조회 (공개, 인증 불필요)
    # ------------------------------------------------------------------

    def get_invitation_by_token(self, token: str) -> InvitationResponse:
        """
        토큰으로 초대 정보 조회 (공개 엔드포인트)

        pending 상태에서 만료된 경우 lazy expire 처리를 수행한다.

        Args:
            token: URL에 포함된 UUID 문자열

        Returns:
            InvitationResponse

        Raises:
            NotFoundException: 토큰이 존재하지 않는 경우
        """
        try:
            parsed_token = UUID(token)
        except (ValueError, AttributeError):
            raise NotFoundException("Invalid invitation token")

        invitation = self.invitation_repository.find_by_token(parsed_token)
        if not invitation:
            raise NotFoundException("Invitation not found")

        # lazy expire: pending이고 만료된 경우 상태 업데이트
        if (
            invitation.status == "pending"
            and invitation.expires_at < datetime.now(timezone.utc)
        ):
            try:
                self.invitation_repository.update_status(invitation, status="expired")
                self.db.commit()
            except Exception:
                self.db.rollback()
                # expire 업데이트 실패 시 현재 상태 그대로 반환 (조회 실패로 처리하지 않음)

        family_name = invitation.family.family_name if invitation.family else ""
        inviter_name = (
            invitation.inviter.name or invitation.inviter.email
            if invitation.inviter
            else ""
        )
        return _build_invitation_response(invitation, family_name, inviter_name)

    # ------------------------------------------------------------------
    # 5. 초대 수락
    # ------------------------------------------------------------------

    def accept_invitation(self, actor_user_id: int, token: str) -> AcceptInvitationResponse:
        """
        초대 수락

        수락 시 현재 family_member를 탈퇴시키고 초대된 family로 이동한다.
        기존 family가 본인만 있는 경우 family 자체도 삭제한다.

        Args:
            actor_user_id: 수락하는 유저 ID
            token: 초대 토큰 UUID 문자열

        Returns:
            AcceptInvitationResponse: 이동한 가족 정보

        Raises:
            NotFoundException: 초대를 찾을 수 없는 경우
            BadRequestException: 초대가 pending + 유효 상태가 아닌 경우
            ForbiddenException: 이메일이 일치하지 않는 경우
            ConflictException: 이미 해당 family 멤버이거나, 다른 family owner인 경우
        """
        try:
            parsed_token = UUID(token)
        except (ValueError, AttributeError):
            raise NotFoundException("Invalid invitation token")

        invitation = self.invitation_repository.find_by_token(parsed_token)
        if not invitation:
            raise NotFoundException("Invitation not found")

        if invitation.status != "pending":
            raise BadRequestException(f"Invitation is already {invitation.status}")

        if invitation.expires_at < datetime.now(timezone.utc):
            # lazy expire 처리 후 예외
            try:
                self.invitation_repository.update_status(invitation, status="expired")
                self.db.commit()
            except Exception:
                self.db.rollback()
            raise BadRequestException("Invitation has expired")

        actor = self.user_repository.find_by_id(actor_user_id)
        if not actor:
            raise NotFoundException("User not found")

        # 이메일 일치 검증 (대소문자 무시)
        if actor.email.strip().lower() != invitation.email.strip().lower():
            raise ForbiddenException("This invitation is not for you")

        target_family_id = invitation.family_id
        target_family = self.family_repository.find_by_id(target_family_id)
        if not target_family:
            raise NotFoundException("Target family not found")

        # 이미 해당 family 멤버인 경우
        already_member = self.family_member_repository.find_by_family_id_and_user_id(
            target_family_id, actor.id
        )
        if already_member:
            raise ConflictException("You are already a member of this family")

        # 현재 family_member 조회
        current_member = self.family_member_repository.find_by_user_id(actor.id)
        if not current_member:
            raise BadRequestException("User is not assigned to a family")

        current_family = self.family_repository.find_by_id(current_member.family_id)

        # 현재 family의 멤버 수 확인
        current_family_members = self.family_member_repository.find_all_by_family_id(
            current_member.family_id
        )
        current_member_count = len(current_family_members)

        # 다른 family의 owner이면서 본인 외 멤버가 있으면 수락 불가
        if (
            current_family
            and current_family.owner_user_id == actor.id
            and current_member.role == "owner"
            and current_member_count > 1
        ):
            raise ConflictException(
                "You are the owner of another family with members. "
                "Transfer ownership or remove members first."
            )

        try:
            # 1. 현재 user_device 연결 해제
            current_device = self.device_repository.find_by_family_id(current_member.family_id)
            if current_device:
                current_user_device = self.user_device_repository.find_by_user_and_device(
                    actor.id, current_device.id
                )
                if current_user_device:
                    self.user_device_repository.delete(current_user_device)

            # 2. 현재 family_member 삭제
            self.family_member_repository.delete(current_member)

            # 3. 현재 family가 본인만 있고 owner였으면 device 연결만 해제
            #    (families 하위 items/tags/master_tags 등에 ON DELETE CASCADE 미설정 FK가
            #     있어 family 자체를 삭제하면 IntegrityError로 500 발생함.
            #     빈 family는 멤버가 없어 아무도 조회 불가하므로 남겨둬도 무해하며,
            #     정리는 별도 배치/관리 엔드포인트로 분리한다.)
            if (
                current_family
                and current_family.owner_user_id == actor.id
                and current_member_count == 1
            ):
                orphan_device = self.device_repository.find_by_family_id(current_family.id)
                if orphan_device:
                    self.device_repository.clear_family(orphan_device)

            # 4. 새 family_member 생성
            new_member = self.family_member_repository.create(
                family_id=target_family_id,
                user_id=actor.id,
                role="member",
            )

            # 5. 새 family의 device에 user_device 생성
            target_device = self.device_repository.find_by_family_id(target_family_id)
            if target_device:
                existing_ud = self.user_device_repository.find_by_user_and_device(
                    actor.id, target_device.id
                )
                if not existing_ud:
                    self.user_device_repository.create(actor.id, target_device.id)

            # 6. 초대 상태 업데이트
            self.invitation_repository.update_status(
                invitation,
                status="accepted",
                timestamp_field="accepted_at",
                timestamp_value=datetime.now(timezone.utc),
            )

            self.db.commit()

            return AcceptInvitationResponse(
                family_id=target_family_id,
                family_name=target_family.family_name,
                role="member",
            )
        except Exception:
            self.db.rollback()
            raise

    # ------------------------------------------------------------------
    # 6. 초대 거절
    # ------------------------------------------------------------------

    def decline_invitation(self, actor_user_id: int, token: str) -> DeclineInvitationResponse:
        """
        초대 거절

        인증된 사용자만 거절 가능하며, 이메일이 일치해야 한다.

        Args:
            actor_user_id: 거절하는 유저 ID
            token: 초대 토큰 UUID 문자열

        Returns:
            DeclineInvitationResponse

        Raises:
            NotFoundException: 초대를 찾을 수 없는 경우
            BadRequestException: 초대가 pending이 아닌 경우
            ForbiddenException: 이메일이 일치하지 않는 경우
        """
        try:
            parsed_token = UUID(token)
        except (ValueError, AttributeError):
            raise NotFoundException("Invalid invitation token")

        invitation = self.invitation_repository.find_by_token(parsed_token)
        if not invitation:
            raise NotFoundException("Invitation not found")

        if invitation.status != "pending":
            raise BadRequestException(f"Invitation is already {invitation.status}")

        actor = self.user_repository.find_by_id(actor_user_id)
        if not actor:
            raise NotFoundException("User not found")

        if actor.email.strip().lower() != invitation.email.strip().lower():
            raise ForbiddenException("This invitation is not for you")

        try:
            self.invitation_repository.update_status(
                invitation,
                status="declined",
                timestamp_field="declined_at",
                timestamp_value=datetime.now(timezone.utc),
            )
            self.db.commit()
            return DeclineInvitationResponse(status="declined")
        except Exception:
            self.db.rollback()
            raise


# ------------------------------------------------------------------
# 내부 헬퍼 함수
# ------------------------------------------------------------------

def _ensure_owner(actor_user_id: int, role: str, owner_user_id: int) -> None:
    """actor가 family owner인지 검증"""
    if role != "owner" or actor_user_id != owner_user_id:
        raise ForbiddenException("Only family owner can manage invitations")


def _build_invitation_response(
    invitation,
    family_name: str,
    inviter_name: str,
) -> InvitationResponse:
    """FamilyInvitation 엔티티 → InvitationResponse 변환"""
    return InvitationResponse(
        id=invitation.id,
        family_id=invitation.family_id,
        family_name=family_name,
        inviter_name=inviter_name,
        email=invitation.email,
        status=invitation.status,
        expires_at=invitation.expires_at,
        created_at=invitation.created_at,
    )
