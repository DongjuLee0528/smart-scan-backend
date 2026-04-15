"""
라벨(태그) 조회 API 라우터

사용자가 새로운 아이템을 등록할 때 연결 가능한 RFID 태그 목록을 조회하는 API를 제공합니다.
물리적 RFID 태그(마스터 태그) 중에서 아직 아이템과 연결되지 않은 사용 가능한 태그들을 반환합니다.

주요 엔드포인트:
- GET /available: 사용 가능한 태그 목록 조회

비즈니스 로직:
- 사용자가 등록한 디바이스의 태그만 조회 가능
- 이미 활성 아이템과 연결된 태그는 제외
- 태그 UID와 등록 시간 정보 제공

보안: JWT 인증 필요, 사용자는 본인 디바이스의 태그만 조회 가능
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.common.dependencies import get_current_user
from backend.common.db import get_db
from backend.common.response import success_response
from backend.common.route_decorators import handle_service_errors
from backend.services.label_service import LabelService


router = APIRouter(tags=["labels"])


@router.get("/available", response_model=dict)
@handle_service_errors
def get_available_labels(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    label_service = LabelService(db)
    result = label_service.get_available_labels(current_user.id)
    return success_response(data=result.model_dump())