from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ItemAddRequest(BaseModel):
    kakao_user_id: str
    name: str
    label_id: int


class ItemUpdateRequest(BaseModel):
    kakao_user_id: str
    name: Optional[str] = None
    label_id: Optional[int] = None


class ItemResponse(BaseModel):
    id: int
    name: str
    label_id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class ItemListResponse(BaseModel):
    items: list[ItemResponse]
    total_count: int