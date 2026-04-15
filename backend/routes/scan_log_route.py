"""
스캔 로그 관리 API 라우터

RFID 스캔 이벤트의 기록과 조회를 위한 API 엔드포인트를 제공합니다.
각 스캔 이벤트는 FOUND/LOST 상태로 기록되며, 소지품 추적의 기본 데이터를 제공합니다.

주요 엔드포인트:
- POST /: 새로운 스캔 로그 등록 (수동)
- GET /{member_id}: 특정 가족 구성원의 스캔 이력 조회

비즈니스 로직:
- 스캔 로그는 주로 Lambda 함수에서 자동 생성
- 수동 등록도 지원 (디버깅 및 테스트용)
- 가족 구성원만 서로의 스캔 이력 조회 가능
- Rate limiting 적용 (API 남용 방지)

데이터 형식:
- 스캔 시간 (UTC)
- 태그 UID
- 스캔 상태 (FOUND/LOST)
- 연관된 아이템 정보

보안: JWT 인증 필요, 가족 단위 데이터 격리
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.common.dependencies import get_current_user
from backend.common.db import get_db
from backend.common.exceptions import BadRequestException
from backend.common.response import success_response
from backend.common.route_decorators import handle_service_errors, validate_positive_id
from backend.common.rate_limiter import limiter, api_rate_limit
from backend.schemas.scan_log_schema import ScanLogCreateRequest
from backend.services.scan_log_service import ScanLogService


router = APIRouter(tags=["scan-logs"])


@router.post("", response_model=dict)
@limiter.limit(api_rate_limit)
@handle_service_errors
def create_scan_log(
    request: ScanLogCreateRequest,
    http_request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    validate_positive_id("item_id", request.item_id or 0)

    scan_log_service = ScanLogService(db)
    result = scan_log_service.create_scan_log(
        user_id=current_user.id,
        item_id=request.item_id,
        status=request.status
    )
    return success_response(data=result.model_dump())
