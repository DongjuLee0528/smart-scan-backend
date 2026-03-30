from pydantic import BaseModel, validator
from datetime import datetime
from enum import Enum


class ScanStatus(str, Enum):
    FOUND = "FOUND"
    LOST = "LOST"


class ScanLogCreateRequest(BaseModel):
    kakao_user_id: str
    item_id: int
    status: ScanStatus


class ScanLogResponse(BaseModel):
    id: int
    user_device_id: int
    item_id: int
    status: ScanStatus
    scanned_at: datetime

    class Config:
        from_attributes = True