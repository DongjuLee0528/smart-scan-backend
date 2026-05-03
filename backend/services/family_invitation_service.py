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
    Family invitation service class

    Inherits from ServiceBase to utilize actor context lookup and common repositories.
    """

    def __init__(self, db: Session):
        super().__init__(db)
        self.invitation_repository = FamilyInvitationRepository(db)
        self.device_repository = DeviceRepository(db)
        self.user_device_repository = UserDeviceRepository(db)
        self.email_service = EmailService()

    # ------------------------------------------------------------------
    # 1. Create invitation
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
        Create family invitation and send email

        Rolls back if email sending fails to ensure data consistency.

        Args:
            actor_user_id: User ID sending the invitation (must be family owner)
            name: Invitee name (for reference)
            email: Invitee email
            phone_number: Invitee phone number (for reference)
            age: Invitee age (for reference, nullable)

        Returns:
            InvitationResponse: Created invitation information

        Raises:
            ForbiddenException: If actor is not family owner
            BadRequestException: If trying to invite oneself
            ConflictException: If duplicate (family, email) pending invitation exists or already a member
        """
        actor, actor_family_member, family = self._get_actor_context(actor_user_id)
        _ensure_owner(actor.id, actor_family_member.role, family.owner_user_id)

        normalized_email = email.strip().lower()

        # Prevent self-invitation
        if actor.email and actor.email.strip().lower() == normalized_email:
            raise BadRequestException("Cannot invite yourself")

        # Check for duplicate pending invitation
        existing_invitation = self.invitation_repository.find_pending_by_family_and_email(
            family.id, normalized_email
        )
        if existing_invitation:
            raise ConflictException("An active invitation already exists for this email")

        # Check if already a member of the family
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
            # Send email after flush when token is confirmed — exception propagates on failure for rollback
            self.email_service.send_invitation_email(
                to_email=normalized_email,
                inviter_name=actor.name or actor.email,
                family_name=family.family_name,
                token=str(invitation.token),
                expires_at=expires_at,
            )
            self.db.commit()
            # Reload relationships after commit
            self.db.refresh(invitation)
            return _build_invitation_response(invitation, family.family_name, actor.name or actor.email)
        except Exception:
            self.db.rollback()
            raise

    # ------------------------------------------------------------------
    # 2. Retrieve invitation list (owner)
    # ------------------------------------------------------------------

    def list_invitations(self, actor_user_id: int) -> InvitationListResponse:
        """
        Retrieve pending invitation list for current family (excluding expired items)

        Args:
            actor_user_id: User ID requesting the list (must be family owner)

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
    # 3. Cancel invitation
    # ------------------------------------------------------------------

    def cancel_invitation(self, actor_user_id: int, invitation_id: int) -> bool:
        """
        Cancel invitation (status: pending → cancelled)

        Args:
            actor_user_id: User ID requesting cancellation (must be family owner)
            invitation_id: Invitation ID to cancel

        Returns:
            True

        Raises:
            NotFoundException: If invitation not found
            ForbiddenException: If invitation doesn't belong to the family
            BadRequestException: If no longer pending
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
    # 4. Retrieve invitation info by token (public, no auth required)
    # ------------------------------------------------------------------

    def get_invitation_by_token(self, token: str) -> InvitationResponse:
        """
        Retrieve invitation information by token (public endpoint)

        Performs lazy expire processing if pending but expired.

        Args:
            token: UUID string included in URL

        Returns:
            InvitationResponse

        Raises:
            NotFoundException: If token doesn't exist
        """
        try:
            parsed_token = UUID(token)
        except (ValueError, AttributeError):
            raise NotFoundException("Invalid invitation token")

        invitation = self.invitation_repository.find_by_token(parsed_token)
        if not invitation:
            raise NotFoundException("Invitation not found")

        # lazy expire: update status if pending and expired
        if (
            invitation.status == "pending"
            and invitation.expires_at < datetime.now(timezone.utc)
        ):
            try:
                self.invitation_repository.update_status(invitation, status="expired")
                self.db.commit()
            except Exception:
                self.db.rollback()
                # Return current state as-is if expire update fails (don't treat as lookup failure)

        family_name = invitation.family.family_name if invitation.family else ""
        inviter_name = (
            invitation.inviter.name or invitation.inviter.email
            if invitation.inviter
            else ""
        )
        return _build_invitation_response(invitation, family_name, inviter_name)

    # ------------------------------------------------------------------
    # 5. Accept invitation
    # ------------------------------------------------------------------

    def accept_invitation(self, actor_user_id: int, token: str) -> AcceptInvitationResponse:
        """
        Accept invitation

        When accepted, removes current family_member and moves to invited family.
        If existing family has only the user, deletes family itself.

        Args:
            actor_user_id: User ID accepting the invitation
            token: Invitation token UUID string

        Returns:
            AcceptInvitationResponse: Information about the new family

        Raises:
            NotFoundException: If invitation not found
            BadRequestException: If invitation is not pending + valid
            ForbiddenException: If email doesn't match
            ConflictException: If already a member of the family or owner of another family
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
            # Lazy expire processing then exception
            try:
                self.invitation_repository.update_status(invitation, status="expired")
                self.db.commit()
            except Exception:
                self.db.rollback()
            raise BadRequestException("Invitation has expired")

        actor = self.user_repository.find_by_id(actor_user_id)
        if not actor:
            raise NotFoundException("User not found")

        # Verify email match (case insensitive)
        if actor.email.strip().lower() != invitation.email.strip().lower():
            raise ForbiddenException("This invitation is not for you")

        target_family_id = invitation.family_id
        target_family = self.family_repository.find_by_id(target_family_id)
        if not target_family:
            raise NotFoundException("Target family not found")

        # If already a member of the family
        already_member = self.family_member_repository.find_by_family_id_and_user_id(
            target_family_id, actor.id
        )
        if already_member:
            raise ConflictException("You are already a member of this family")

        # Lookup current family_member
        current_member = self.family_member_repository.find_by_user_id(actor.id)
        if not current_member:
            raise BadRequestException("User is not assigned to a family")

        current_family = self.family_repository.find_by_id(current_member.family_id)

        # Check member count of current family
        current_family_members = self.family_member_repository.find_all_by_family_id(
            current_member.family_id
        )
        current_member_count = len(current_family_members)

        # Cannot accept if owner of another family with members other than self
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
            # 1. Disconnect current user_device
            current_device = self.device_repository.find_by_family_id(current_member.family_id)
            if current_device:
                current_user_device = self.user_device_repository.find_by_user_and_device(
                    actor.id, current_device.id
                )
                if current_user_device:
                    self.user_device_repository.delete(current_user_device)

            # 2. Delete current family_member
            self.family_member_repository.delete(current_member)

            # 3. If current family only has self and was owner, only disconnect device
            #    (FK constraints without ON DELETE CASCADE under families for items/tags/master_tags
            #     would cause IntegrityError 500 if family itself is deleted.
            #     Empty families are harmless as no one can access them without members,
            #     cleanup is separated to batch/admin endpoints.)
            if (
                current_family
                and current_family.owner_user_id == actor.id
                and current_member_count == 1
            ):
                orphan_device = self.device_repository.find_by_family_id(current_family.id)
                if orphan_device:
                    self.device_repository.clear_family(orphan_device)

            # 4. Create new family_member
            new_member = self.family_member_repository.create(
                family_id=target_family_id,
                user_id=actor.id,
                role="member",
            )

            # 5. Create user_device for new family's device
            target_device = self.device_repository.find_by_family_id(target_family_id)
            if target_device:
                existing_ud = self.user_device_repository.find_by_user_and_device(
                    actor.id, target_device.id
                )
                if not existing_ud:
                    self.user_device_repository.create(actor.id, target_device.id)

            # 6. Update invitation status
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
    # 6. Decline invitation
    # ------------------------------------------------------------------

    def decline_invitation(self, actor_user_id: int, token: str) -> DeclineInvitationResponse:
        """
        Decline invitation

        Only authenticated users can decline, and email must match.

        Args:
            actor_user_id: User ID declining the invitation
            token: Invitation token UUID string

        Returns:
            DeclineInvitationResponse

        Raises:
            NotFoundException: If invitation not found
            BadRequestException: If invitation is not pending
            ForbiddenException: If email doesn't match
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
# Internal helper functions
# ------------------------------------------------------------------

def _ensure_owner(actor_user_id: int, role: str, owner_user_id: int) -> None:
    """Verify if actor is family owner"""
    if role != "owner" or actor_user_id != owner_user_id:
        raise ForbiddenException("Only family owner can manage invitations")


def _build_invitation_response(
    invitation,
    family_name: str,
    inviter_name: str,
) -> InvitationResponse:
    """Convert FamilyInvitation entity → InvitationResponse"""
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
