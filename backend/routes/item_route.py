"""
Item management API router

Provides REST API for managing items connected to smart tags.
Includes endpoints for users to register, modify, delete, and retrieve real objects connected to tags.

Main endpoints:
- GET /items: Retrieve all family item list
- POST /items: Register new item
- PUT /items/{item_id}: Modify item information
- DELETE /items/{item_id}: Delete item (cascade delete)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.common.dependencies import get_current_user
from backend.common.db import get_db
from backend.common.response import success_response
from backend.common.route_decorators import handle_service_errors
from backend.schemas.item_schema import ItemAddRequest, ItemBindRequest, ItemUpdateRequest
from backend.services.item_service import ItemService


router = APIRouter(tags=["items"])


@router.get("", response_model=dict)
@handle_service_errors
def get_items(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve item list

    Retrieve all items from the family that the logged-in user belongs to.
    Returns both pending status and regular items.

    Returns:
        All item list and total count for the family

    Raises:
        AuthenticationError: When authentication token is invalid
        ForbiddenError: When user doesn't belong to a family
    """
    item_service = ItemService(db)
    result = item_service.get_items(current_user.id)
    return success_response(data=result.model_dump())


@router.post("", response_model=dict)
@handle_service_errors
def add_item(
    request: ItemAddRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    item_service = ItemService(db)
    result = item_service.add_item(
        user_id=current_user.id,
        name=request.name,
        label_id=request.label_id
    )
    return success_response(data=result.model_dump())


@router.patch("/{item_id}/bind", response_model=dict)
@handle_service_errors
def bind_item(
    item_id: int,
    request: ItemBindRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Connect label (master tag) to pending item that was added with name only from chatbot."""
    item_service = ItemService(db)
    result = item_service.bind_item(
        item_id=item_id,
        user_id=current_user.id,
        label_id=request.label_id,
    )
    return success_response(data=result.model_dump())


@router.patch("/{item_id}", response_model=dict)
@handle_service_errors
def update_item(
    item_id: int,
    request: ItemUpdateRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    item_service = ItemService(db)
    result = item_service.update_item(
        item_id=item_id,
        user_id=current_user.id,
        name=request.name,
        label_id=request.label_id
    )
    return success_response(data=result.model_dump())


@router.delete("/{item_id}", response_model=dict)
@handle_service_errors
def delete_item(
    item_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    item_service = ItemService(db)
    result = item_service.delete_item(item_id, current_user.id)
    return success_response(data={"deleted": result})