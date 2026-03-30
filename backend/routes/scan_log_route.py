from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.services.scan_log_service import ScanLogService
from backend.schemas.scan_log_schema import ScanLogCreateRequest
from backend.common.db import get_db
from backend.common.response import success_response
from backend.common.exceptions import handle_exceptions

router = APIRouter(prefix="/scan-logs", tags=["scan-logs"])


@router.post("", response_model=dict)
@handle_exceptions
def create_scan_log(
    request: ScanLogCreateRequest,
    db: Session = Depends(get_db)
):
    scan_log_service = ScanLogService(db)
    result = scan_log_service.create_scan_log(
        kakao_user_id=request.kakao_user_id,
        item_id=request.item_id,
        status=request.status
    )
    return success_response(data=result.dict())