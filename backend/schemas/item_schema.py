"""
소지품(아이템) 관리 API 스키마

RFID 태그와 연결되는 실제 소지품의 생성, 수정, 조회를 위한 API 스키마를 정의합니다.
사용자의 소지품 등록과 관리를 위한 데이터 구조를 제공합니다.

A-full (2026-04-18):
- is_pending 추가 — 챗봇에서 이름만 추가된 "라벨 연결 대기" 아이템
- label_id는 pending 상태일 때 NULL 허용
- ItemBindRequest: 라벨 연결 전용 스키마
- ChatbotItemCreateRequest / ChatbotItemDeleteByNameRequest / ChatbotDeviceUnlinkRequest: 챗봇 전용 스키마
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
    """Pending 아이템에 라벨을 연결하여 활성 아이템으로 전환."""
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
