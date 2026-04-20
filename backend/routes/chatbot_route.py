"""
Chatbot (Kakao OpenBuilder) 전용 서비스-투-서비스 API

smartscan-chatbot Lambda가 카카오 웹훅 처리 중 SmartScan 백엔드에 호출하는
내부 API를 정의한다. kakao_user_id 기반으로 사용자를 식별하며, 인증은
JWT가 아니라 X-Chatbot-Key 공유 비밀키 헤더로 수행된다.

엔드포인트:
- GET  /api/chatbot/items?kakao_user_id=...     : 활성 아이템 목록 (pending 포함)
- POST /api/chatbot/items                        : 이름만으로 pending 아이템 추가
- POST /api/chatbot/items/delete-by-name         : 이름으로 아이템 소프트 삭제
- POST /api/chatbot/device/unlink                : 모든 활성 아이템 일괄 삭제 (기기 해제)
- POST /api/chatbot/users/resolve                : kakao_user_id → user 기본 정보 (옵션)

A-full (2026-04-18): pending 아이템 지원을 위해 도입.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.common.chatbot_auth import require_chatbot_key
from backend.common.db import get_db
from backend.common.response import success_response
from backend.common.route_decorators import handle_service_errors
from backend.schemas.item_schema import (
    ChatbotDeviceUnlinkRequest,
    ChatbotItemCreateRequest,
    ChatbotItemDeleteByNameRequest,
    ChatbotUserResolveRequest,
)
from backend.services.item_service import ItemService


router = APIRouter(tags=["chatbot"], dependencies=[Depends(require_chatbot_key)])


@router.get("/items", response_model=dict)
@handle_service_errors
def chatbot_list_items(
    kakao_user_id: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    service = ItemService(db)
    result = service.chatbot_list_items(kakao_user_id)
    return success_response(data=result.model_dump())


@router.post("/items", response_model=dict)
@handle_service_errors
def chatbot_add_pending_item(
    request: ChatbotItemCreateRequest,
    db: Session = Depends(get_db),
):
    service = ItemService(db)
    result = service.chatbot_add_pending_item(request.kakao_user_id, request.name)
    return success_response(data=result.model_dump())


@router.post("/items/delete-by-name", response_model=dict)
@handle_service_errors
def chatbot_delete_by_name(
    request: ChatbotItemDeleteByNameRequest,
    db: Session = Depends(get_db),
):
    service = ItemService(db)
    deleted = service.chatbot_delete_by_name(request.kakao_user_id, request.name)
    return success_response(data={"deleted_count": deleted})


@router.post("/device/unlink", response_model=dict)
@handle_service_errors
def chatbot_unlink_device(
    request: ChatbotDeviceUnlinkRequest,
    db: Session = Depends(get_db),
):
    service = ItemService(db)
    deleted = service.chatbot_unlink_device(request.kakao_user_id)
    return success_response(data={"deleted_count": deleted})


@router.post("/users/resolve", response_model=dict)
@handle_service_errors
def chatbot_resolve_user(
    request: ChatbotUserResolveRequest,
    db: Session = Depends(get_db),
):
    """kakao_user_id → user_device 존재 여부 확인. 챗봇이 기기 연결 여부를 간단히 판별."""
    service = ItemService(db)
    user_device = service._get_kakao_user_device(request.kakao_user_id)
    return success_response(data={
        "user_id": user_device.user_id,
        "device_id": user_device.device_id,
        "family_id": user_device.device.family_id,
    })
