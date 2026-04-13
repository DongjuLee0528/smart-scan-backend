"""
RFID 태그 관리 API 라우터

RFID 태그와 아이템 간의 연결을 관리하는 API 엔드포인트를 제공합니다.
물리적 RFID 태그를 시스템에 등록하고 소지품과 연결하여 추적을 가능하게 합니다.

주요 엔드포인트:
- POST /: 새로운 RFID 태그 등록 및 아이템 연결
- GET /: 현재 사용자의 모든 등록된 태그 목록 조회
- PUT /{tag_id}: 태그 정보 수정 (연결된 아이템 변경)
- DELETE /{tag_id}: 태그 등록 해제

보안: 사용자는 본인이 등록한 태그만 관리 가능
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.common.dependencies import get_current_user
from backend.common.db import get_db
from backend.common.response import success_response
from backend.common.route_decorators import handle_service_errors
from backend.schemas.tag_schema import CreateTagRequest, UpdateTagRequest
from backend.services.tag_service import TagService


router = APIRouter(tags=["tags"])


def get_tag_service(db: Session = Depends(get_db)) -> TagService:
    return TagService(db)


@router.post("", response_model=dict)
@handle_service_errors
def create_tag(
    request: CreateTagRequest,
    current_user=Depends(get_current_user),
    tag_service: TagService = Depends(get_tag_service)
):
    result = tag_service.create_tag(
        user_id=current_user.id,
        tag_uid=request.tag_uid,
        name=request.name,
        owner_user_id=request.owner_user_id,
        device_id=request.device_id
    )
    return success_response("Tag created successfully", result.model_dump())


@router.get("", response_model=dict)
@handle_service_errors
def get_tags(
    current_user=Depends(get_current_user),
    tag_service: TagService = Depends(get_tag_service)
):
    result = tag_service.get_tags(current_user.id)
    return success_response("Tags retrieved successfully", result.model_dump())


@router.patch("/{tag_id}", response_model=dict)
@handle_service_errors
def update_tag(
    tag_id: int,
    request: UpdateTagRequest,
    current_user=Depends(get_current_user),
    tag_service: TagService = Depends(get_tag_service)
):
    result = tag_service.update_tag(
        tag_id=tag_id,
        user_id=current_user.id,
        name=request.name,
        owner_user_id=request.owner_user_id,
        device_id=request.device_id
    )
    return success_response("Tag updated successfully", result.model_dump())


@router.delete("/{tag_id}", response_model=dict)
@handle_service_errors
def delete_tag(
    tag_id: int,
    current_user=Depends(get_current_user),
    tag_service: TagService = Depends(get_tag_service)
):
    result = tag_service.delete_tag(tag_id, current_user.id)
    return success_response("Tag deleted successfully", {"deleted": result})