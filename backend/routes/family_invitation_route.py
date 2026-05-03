"""
Family invitation API router

Provides invitation creation, lookup, acceptance, decline, and cancellation endpoints under /api/family-invitations prefix.

Endpoints:
- POST   /                 : Create invitation (owner only)
- GET    /                 : Pending invitation list lookup (owner only)
- DELETE /{invitation_id}  : Cancel invitation (owner only)
- GET    /by-token/{token} : Invitation info lookup (public)
- POST   /{token}/accept   : Accept invitation (authentication required)
- POST   /{token}/decline  : Decline invitation (authentication required)
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
    Create invitation (family owner only)

    Includes name, email, phone number, and age (optional) in the request body.
    Invitation email is sent, and invitation record is rolled back if sending fails.
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
    Retrieve pending invitation list (family owner only)

    Expired invitations are not included in the list.
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
    Cancel invitation (family owner only)

    Only invitations in pending status can be cancelled.
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
    Retrieve invitation information by token (public, no authentication required)

    If pending but expired, performs lazy expire processing and returns with status='expired'.
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
    Accept invitation (authentication required)

    When accepted, leaves current family and joins the invited family.
    If current family has only the user, the family itself is also deleted.
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
    Decline invitation (authentication required)

    Only authenticated users with matching email can decline.
    """
    result = service.decline_invitation(current_user.id, token)
    return success_response("Invitation declined", result.model_dump())
