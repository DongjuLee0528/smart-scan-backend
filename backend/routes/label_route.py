from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.services.label_service import LabelService
from backend.common.db import get_db
from backend.common.response import success_response

router = APIRouter(tags=["labels"])


@router.get("/available", response_model=dict)
def get_available_labels(
    kakao_user_id: str = Query(..., description="카카오 사용자 ID"),
    db: Session = Depends(get_db)
):
    label_service = LabelService(db)
    result = label_service.get_available_labels(kakao_user_id)
    return success_response(data=result.model_dump())
