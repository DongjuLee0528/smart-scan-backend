"""
Label (tag) lookup API router

Provides API for querying available RFID tag list that can be connected when user registers new items.
Returns available tags among physical RFID tags (master tags) that are not yet connected to items.

Main endpoints:
- GET /available: Query available tag list

Business logic:
- Only tags from user's registered device can be queried
- Exclude tags already connected to active items
- Provide tag UID and registration time information

Security: JWT authentication required, users can only query tags from their own devices
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