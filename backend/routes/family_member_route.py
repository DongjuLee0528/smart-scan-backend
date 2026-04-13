"""
가족 구성원 관리 API 라우터

SmartScan 시스템에서 가족 그룹 내 구성원을 관리하는 API 엔드포인트를 제공합니다.
가족 구성원을 추가하고 삭제하며, 각 구성원의 소지품을 개별적으로 추적할 수 있습니다.

주요 엔드포인트:
- POST /: 새로운 가족 구성원 추가
- GET /: 현재 가족의 모든 구성원 목록 조회
- DELETE /{member_id}: 가족 구성원 제거

권한: 가족 소유자만 구성원 추가/삭제 가능
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