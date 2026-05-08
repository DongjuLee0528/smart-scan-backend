"""
Virtual Tag Management API Schema

Defines API schemas for creating, updating, and retrieving virtual tags created by users.
Provides logical tag data structures before connection to actual physical RFID tags.

Main Schemas:
- CreateTagRequest: Request to create a new virtual tag
- UpdateTagRequest: Request to update existing tag information
- TagResponse: Tag detailed information response
- TagListResponse: Tag list response

Data Structure:
- Tag unique identifier (tag_uid)
- Tag name (user-defined)
- Owner and connected device information
- Active status (deactivated when deleted)

Business Rules:
- Tags must be connected to a specific device
- Tag UID must be unique across the entire system
- Only family members can view tags of their family
- Only owners can modify/delete tags
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


def _validate_required_text(value: str, field_name: str) -> str:
    normalized_value = value.strip()
    if not normalized_value:
        raise ValueError(f"{field_name} is required")
    return normalized_value


def _normalize_optional_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None

    normalized_value = value.strip()
    return normalized_value or None


class CreateTagRequest(BaseModel):
    tag_uid: str
    name: str
    owner_user_id: int
    device_id: int

    @field_validator("tag_uid", "name")
    @classmethod
    def validate_required_text(cls, v: str, info) -> str:
        return _validate_required_text(v, info.field_name)


class UpdateTagRequest(BaseModel):
    name: Optional[str] = None
    owner_user_id: Optional[int] = None
    device_id: Optional[int] = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: Optional[str]) -> Optional[str]:
        return _normalize_optional_text(v)


class TagResponse(BaseModel):
    id: int
    tag_uid: str
    name: str
    family_id: int
    owner_user_id: int
    device_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TagListResponse(BaseModel):
    tags: list[TagResponse]
    total_count: int
