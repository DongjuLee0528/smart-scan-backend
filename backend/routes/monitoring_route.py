"""
Monitoring API router

Provides REST API endpoints for Smart Scan tag monitoring.
Includes APIs for monitoring tag status at family level and querying individual member tag states.

Main endpoints:
- GET /dashboard: Family-wide tag monitoring dashboard
- GET /member/{member_id}/tags: Specific member's tag list
- GET /my-tags: My tag status list
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