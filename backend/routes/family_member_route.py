"""
Family member management API router

Provides API endpoints for managing members within family groups in SmartScan system.
Allows adding and removing family members, and individually tracking each member's belongings.

Main endpoints:
- POST /: Add new family member
- GET /: Query all member list of current family
- DELETE /{member_id}: Remove family member

Permissions: Only family owners can add/remove members
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.common.dependencies import get_current_user
from backend.common.db import get_db
from backend.common.response import success_response
from backend.common.route_decorators import handle_service_errors
from backend.schemas.family_member_schema import AddFamilyMemberRequest
from backend.services.family_member_service import FamilyMemberService


router = APIRouter(tags=["family-members"])


def get_family_member_service(db: Session = Depends(get_db)) -> FamilyMemberService:
    return FamilyMemberService(db)


@router.post("", response_model=dict)
@handle_service_errors
def add_family_member(
    request: AddFamilyMemberRequest,
    current_user=Depends(get_current_user),
    family_member_service: FamilyMemberService = Depends(get_family_member_service)
):
    result = family_member_service.add_member(
        user_id=current_user.id,
        name=request.name,
        email=request.email,
        phone_number=request.phone_number,
        age=request.age
    )
    return success_response("Family member added successfully", result.model_dump())


@router.get("", response_model=dict)
@handle_service_errors
def get_family_members(
    current_user=Depends(get_current_user),
    family_member_service: FamilyMemberService = Depends(get_family_member_service)
):
    result = family_member_service.get_members(current_user.id)
    return success_response("Family members retrieved successfully", result.model_dump())


@router.delete("/{member_id}", response_model=dict)
@handle_service_errors
def delete_family_member(
    member_id: int,
    current_user=Depends(get_current_user),
    family_member_service: FamilyMemberService = Depends(get_family_member_service)
):
    result = family_member_service.delete_member(current_user.id, member_id)
    return success_response("Family member deleted successfully", {"deleted": result})