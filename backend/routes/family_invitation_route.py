"""
가족 초대 API 라우터

/api/family-invitations 프리픽스 하에 초대 생성, 조회, 수락, 거절, 취소 엔드포인트를 제공합니다.

엔드포인트:
- POST   /                 : 초대 생성 (owner 전용)
- GET    /                 : pending 초대 목록 조회 (owner 전용)
- DELETE /{invitation_id}  : 초대 취소 (owner 전용)
- GET    /by-token/{token} : 초대 정보 조회 (공개)
- POST   /{token}/accept   : 초대 수락 (인증 필요)
- POST   /{token}/decline  : 초대 거절 (인증 필요)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.common.db import get_db
from backend.common.dependencies import get_current_user
from backend.common.response import success_response
from backend.common.route_decorators import handle_service_errors
from backend.schemas.family_invitation_schema import CreateInvitationRequest
from backend.services.family_invitation_service import FamilyInvitationService

router = APIRouter(tags=["family-invitations"])


def get_invitation_service(db: Session = Depends(get_db)) -> FamilyInvitationService:
    return FamilyInvitationService(db)


@router.post("", response_model=dict)
@handle_service_errors
def create_invitation(
    request: CreateInvitationRequest,
    current_user=Depends(get_current_user),
    service: FamilyInvitationService = Depends(get_invitation_service),
):
    """
    초대 생성 (family owner 전용)

    본문에 이름, 이메일, 전화번호, 나이(선택)를 포함한다.
    초대 이메일이 발송되며, 발송 실패 시 초대 레코드도 rollback된다.
    """
    result = service.create_invitation(
        actor_user_id=current_user.id,
        name=request.name,
        email=request.email,
        phone_number=request.phone_number,
        age=request.age,
    )
    return success_response(
        "Invitation sent successfully. An email has been delivered to the invitee.",
        result.model_dump(),
    )


@router.get("", response_model=dict)
@handle_service_errors
def list_invitations(
    current_user=Depends(get_current_user),
    service: FamilyInvitationService = Depends(get_invitation_service),
):
    """
    pending 초대 목록 조회 (family owner 전용)

    만료된 초대는 목록에 포함되지 않는다.
    """
    result = service.list_invitations(current_user.id)
    return success_response("Pending invitations retrieved successfully", result.model_dump())


@router.delete("/{invitation_id}", response_model=dict)
@handle_service_errors
def cancel_invitation(
    invitation_id: int,
    current_user=Depends(get_current_user),
    service: FamilyInvitationService = Depends(get_invitation_service),
):
    """
    초대 취소 (family owner 전용)

    pending 상태의 초대만 취소 가능하다.
    """
    service.cancel_invitation(current_user.id, invitation_id)
    return success_response("Invitation cancelled successfully", {"cancelled": True})


@router.get("/by-token/{token}", response_model=dict)
@handle_service_errors
def get_invitation_by_token(
    token: str,
    service: FamilyInvitationService = Depends(get_invitation_service),
):
    """
    토큰으로 초대 정보 조회 (공개, 인증 불필요)

    pending이지만 만료된 경우 lazy expire 처리 후 status='expired'로 반환한다.
    """
    result = service.get_invitation_by_token(token)
    return success_response("Invitation retrieved successfully", result.model_dump())


@router.post("/{token}/accept", response_model=dict)
@handle_service_errors
def accept_invitation(
    token: str,
    current_user=Depends(get_current_user),
    service: FamilyInvitationService = Depends(get_invitation_service),
):
    """
    초대 수락 (인증 필요)

    수락 시 현재 family를 탈퇴하고 초대된 family에 합류한다.
    현재 family에 본인만 있는 경우 family 자체도 삭제된다.
    """
    result = service.accept_invitation(current_user.id, token)
    return success_response("Invitation accepted successfully", result.model_dump())


@router.post("/{token}/decline", response_model=dict)
@handle_service_errors
def decline_invitation(
    token: str,
    current_user=Depends(get_current_user),
    service: FamilyInvitationService = Depends(get_invitation_service),
):
    """
    초대 거절 (인증 필요)

    이메일이 일치하는 인증된 사용자만 거절 가능하다.
    """
    result = service.decline_invitation(current_user.id, token)
    return success_response("Invitation declined", result.model_dump())
