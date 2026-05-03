"""
Chatbot (Kakao OpenBuilder) dedicated service-to-service API

Defines internal API that smartscan-chatbot Lambda calls to SmartScan backend during
Kakao webhook processing. Identifies users based on kakao_user_id, and authentication
is performed with X-Chatbot-Key shared secret header rather than JWT.

Endpoints:
- GET  /api/chatbot/items?kakao_user_id=...     : Active item list (includes pending)
- POST /api/chatbot/items                        : Add pending item by name only
- POST /api/chatbot/items/delete-by-name         : Soft delete item by name
- POST /api/chatbot/device/unlink                : Batch delete all active items (device unlink)
- POST /api/chatbot/users/resolve                : kakao_user_id → user basic info (optional)

A-full (2026-04-18): Introduced to support pending items.
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
    """Check kakao_user_id → user_device existence. Simple device connection status check for chatbot."""
    service = ItemService(db)
    user_device = service._get_kakao_user_device(request.kakao_user_id)
    return success_response(data={
        "user_id": user_device.user_id,
        "device_id": user_device.device_id,
        "family_id": user_device.device.family_id,
    })
