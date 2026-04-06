from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.common.dependencies import get_current_user
from backend.common.db import get_db
from backend.common.response import success_response
from backend.schemas.tag_schema import CreateTagRequest, UpdateTagRequest
from backend.services.tag_service import TagService


router = APIRouter(tags=["tags"])


def get_tag_service(db: Session = Depends(get_db)) -> TagService:
    return TagService(db)


@router.post("", response_model=dict)
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
def get_tags(
    current_user=Depends(get_current_user),
    tag_service: TagService = Depends(get_tag_service)
):
    result = tag_service.get_tags(current_user.id)
    return success_response("Tags retrieved successfully", result.model_dump())


@router.patch("/{tag_id}", response_model=dict)
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
def delete_tag(
    tag_id: int,
    current_user=Depends(get_current_user),
    tag_service: TagService = Depends(get_tag_service)
):
    result = tag_service.delete_tag(tag_id, current_user.id)
    return success_response("Tag deleted successfully", {"deleted": result})
