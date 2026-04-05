from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.common.db import get_db
from backend.common.response import success_response
from backend.services.monitoring_service import MonitoringService


router = APIRouter(tags=["monitoring"])


def get_monitoring_service(db: Session = Depends(get_db)) -> MonitoringService:
    return MonitoringService(db)


@router.get("/dashboard", response_model=dict)
def get_dashboard(
    kakao_user_id: str = Query(..., description="카카오 사용자 ID"),
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    result = monitoring_service.get_dashboard(kakao_user_id)
    return success_response(
        message="Monitoring dashboard retrieved successfully",
        data=result.model_dump()
    )


@router.get("/my-tags", response_model=dict)
def get_my_tag_statuses(
    kakao_user_id: str = Query(..., description="카카오 사용자 ID"),
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    result = monitoring_service.get_my_tag_statuses(kakao_user_id)
    return success_response(
        message="Tag statuses retrieved successfully",
        data=result.model_dump()
    )


@router.get("/members/{member_id}/tags", response_model=dict)
def get_member_tags(
    member_id: int,
    kakao_user_id: str = Query(..., description="카카오 사용자 ID"),
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
):
    result = monitoring_service.get_member_tags(kakao_user_id, member_id)
    return success_response(
        message="Member tag statuses retrieved successfully",
        data=result.model_dump()
    )
