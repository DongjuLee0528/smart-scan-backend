"""
RFID tag management API router

Provides API endpoints for managing connections between RFID tags and items.
Enables tracking by registering physical RFID tags to the system and connecting them with belongings.

Main endpoints:
- POST /: Register new RFID tag and connect to item
- GET /: Query all registered tag list of current user
- PUT /{tag_id}: Modify tag information (change connected item)
- DELETE /{tag_id}: Unregister tag

Security: Users can only manage tags they registered themselves
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.common.dependencies import get_current_user
from backend.common.db import get_db
from backend.common.response import success_response
from backend.common.route_decorators import handle_service_errors
from backend.schemas.tag_schema import CreateTagRequest, UpdateTagRequest
from backend.services.tag_service import TagService


router = APIRouter(tags=["tags"])


def get_tag_service(db: Session = Depends(get_db)) -> TagService:
    return TagService(db)


@router.post("", response_model=dict)
@handle_service_errors
def create_tag(
    request: CreateTagRequest,
    current_user=Depends(get_current_user),
    tag_service: TagService = Depends(get_tag_service)
):
    result = tag_service.create_tag(
        user_id=current_user.id,
        tag_uid=request.tag_uid,
        name=request.name,
        owner_user_id=request.owner_user_id,
        device_id=request.device_id
    )
    return success_response("Tag created successfully", result.model_dump())


@router.get("", response_model=dict)
@handle_service_errors
def get_tags(
    current_user=Depends(get_current_user),
    tag_service: TagService = Depends(get_tag_service)
):
    result = tag_service.get_tags(current_user.id)
    return success_response("Tags retrieved successfully", result.model_dump())


@router.patch("/{tag_id}", response_model=dict)
@handle_service_errors
def update_tag(
    tag_id: int,
    request: UpdateTagRequest,
    current_user=Depends(get_current_user),
    tag_service: TagService = Depends(get_tag_service)
):
    result = tag_service.update_tag(
        tag_id=tag_id,
        user_id=current_user.id,
        name=request.name,
        owner_user_id=request.owner_user_id,
        device_id=request.device_id
    )
    return success_response("Tag updated successfully", result.model_dump())


@router.delete("/{tag_id}", response_model=dict)
@handle_service_errors
def delete_tag(
    tag_id: int,
    current_user=Depends(get_current_user),
    tag_service: TagService = Depends(get_tag_service)
):
    result = tag_service.delete_tag(tag_id, current_user.id)
    return success_response("Tag deleted successfully", {"deleted": result})