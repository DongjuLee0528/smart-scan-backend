"""
아이템 관리 API 라우터

스마트 태그와 연결된 물품(아이템) 관리 REST API를 제공한다.
사용자가 태그에 연결할 실제 물건을 등록, 수정, 삭제하고 조회할 수 있는 엔드포인트들을 포함한다.

주요 엔드포인트:
- GET /items: 가족의 모든 아이템 목록 조회
- POST /items: 새로운 아이템 등록
- PUT /items/{item_id}: 아이템 정보 수정
- DELETE /items/{item_id}: 아이템 삭제 (연삭제)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.common.dependencies import get_current_user
from backend.common.db import get_db
from backend.common.response import success_response
from backend.common.route_decorators import handle_service_errors
from backend.schemas.item_schema import ItemAddRequest, ItemBindRequest, ItemUpdateRequest
from backend.services.item_service import ItemService


router = APIRouter(tags=["items"])


@router.get("", response_model=dict)
@handle_service_errors
def get_items(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    아이템 목록 조회

    로그인한 사용자가 속한 가족의 모든 아이템을 조회합니다.
    pending 상태와 일반 아이템을 모두 포함하여 반환합니다.

    Returns:
        가족의 모든 아이템 목록과 총 개수

    Raises:
        AuthenticationError: 인증 토큰이 유효하지 않은 경우
        ForbiddenError: 가족에 속하지 않은 경우
    """
    item_service = ItemService(db)
    result = item_service.get_items(current_user.id)
    return success_response(data=result.model_dump())


@router.post("", response_model=dict)
@handle_service_errors
def add_item(
    request: ItemAddRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    item_service = ItemService(db)
    result = item_service.add_item(
        user_id=current_user.id,
        name=request.name,
        label_id=request.label_id
    )
    return success_response(data=result.model_dump())


@router.patch("/{item_id}/bind", response_model=dict)
@handle_service_errors
def bind_item(
    item_id: int,
    request: ItemBindRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """챗봇에서 이름만 추가된 pending 아이템에 라벨(마스터 태그) 연결."""
    item_service = ItemService(db)
    result = item_service.bind_item(
        item_id=item_id,
        user_id=current_user.id,
        label_id=request.label_id,
    )
    return success_response(data=result.model_dump())


@router.patch("/{item_id}", response_model=dict)
@handle_service_errors
def update_item(
    item_id: int,
    request: ItemUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    item_service = ItemService(db)
    result = item_service.update_item(
        item_id=item_id,
        user_id=current_user.id,
        name=request.name,
        label_id=request.label_id
    )
    return success_response(data=result.model_dump())


@router.delete("/{item_id}", response_model=dict)
@handle_service_errors
def delete_item(
    item_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    item_service = ItemService(db)
    result = item_service.delete_item(item_id, current_user.id)
    return success_response(data={"deleted": result})