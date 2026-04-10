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