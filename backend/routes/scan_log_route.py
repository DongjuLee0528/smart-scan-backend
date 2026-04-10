from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.common.dependencies import get_current_user
from backend.common.db import get_db
from backend.common.exceptions import BadRequestException
from backend.common.response import success_response
from backend.common.route_decorators import handle_service_errors
from backend.schemas.scan_log_schema import ScanLogCreateRequest
from backend.services.scan_log_service import ScanLogService


router = APIRouter(tags=["scan-logs"])


@router.post("", response_model=dict)
@handle_service_errors
def create_scan_log(
    request: ScanLogCreateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if request.item_id is None or request.item_id <= 0:
        raise BadRequestException("item_id는 양수여야 합니다")

    scan_log_service = ScanLogService(db)
    result = scan_log_service.create_scan_log(
        user_id=current_user.id,
        item_id=request.item_id,
        status=request.status
    )
    return success_response(data=result.model_dump())
