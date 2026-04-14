"""
모니터링 API 라우터

Smart Scan 태그 모니터링 관련 REST API 엔드포인트를 제공한다.
가족 단위로 태그 현황을 모니터링하고 개별 구성원의 태그 상태를 조회할 수 있는 API들을 포함한다.

주요 엔드포인트:
- GET /dashboard: 가족 전체 태그 모니터링 대시보드
- GET /member/{member_id}/tags: 특정 구성원의 태그 목록
- GET /my-tags: 내 태그 상태 목록
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.common.dependencies import get_current_user
from backend.common.db import get_db
from backend.common.response import success_response
from backend.common.route_decorators import handle_service_errors
from backend.services.monitoring_service import MonitoringService


router = APIRouter(tags=["monitoring"])


def get_monitoring_service(db: Session = Depends(get_db)) -> MonitoringService:
    return MonitoringService(db)


@router.get("/dashboard", response_model=dict)
@handle_service_errors
def get_dashboard(
    current_user=Depends(get_current_user),
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    result = monitoring_service.get_dashboard(current_user.id)
    return success_response(
        message="Monitoring dashboard retrieved successfully",
        data=result.model_dump()
    )


@router.get("/my-tags", response_model=dict)
@handle_service_errors
def get_my_tag_statuses(
    current_user=Depends(get_current_user),
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    result = monitoring_service.get_my_tag_statuses(current_user.id)
    return success_response(
        message="Tag statuses retrieved successfully",
        data=result.model_dump()
    )


@router.get("/members/{member_id}/tags", response_model=dict)
@handle_service_errors
def get_member_tags(
    member_id: int,
    current_user=Depends(get_current_user),
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    result = monitoring_service.get_member_tags(current_user.id, member_id)
    return success_response(
        message="Member tag statuses retrieved successfully",
        data=result.model_dump()
    )