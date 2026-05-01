"""
Personal belongings (item) management API schemas

Defines API schemas for creating, modifying, and retrieving real belongings connected to RFID tags.
Provides data structures for user belonging registration and management.

A-full (2026-04-18):
- Added is_pending — "waiting for label connection" items with name-only added from chatbot
- label_id allows NULL when in pending state
- ItemBindRequest: Label connection-specific schema
- ChatbotItemCreateRequest / ChatbotItemDeleteByNameRequest / ChatbotDeviceUnlinkRequest: Chatbot-specific schemas
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ItemAddRequest(BaseModel):
    name: str
    label_id: int


class ItemUpdateRequest(BaseModel):
    name: Optional[str] = None
    label_id: Optional[int] = None


class ItemBindRequest(BaseModel):
    """Connect label to pending item to convert to active item."""
    label_id: int


class ItemResponse(BaseModel):
    id: int
    name: str
    label_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool
    is_pending: bool = False

    model_config = ConfigDict(from_attributes=True)


class ItemListResponse(BaseModel):
    items: list[ItemResponse]
    total_count: int


# ---------- Chatbot-facing schemas ----------
class ChatbotItemCreateRequest(BaseModel):
    kakao_user_id: str
    name: str


class ChatbotItemDeleteByNameRequest(BaseModel):
    kakao_user_id: str
    name: str


class ChatbotDeviceUnlinkRequest(BaseModel):
    kakao_user_id: str


class ChatbotUserResolveRequest(BaseModel):
    kakao_user_id: str
