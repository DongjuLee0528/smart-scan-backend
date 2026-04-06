from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict


class ScanStatus(str, Enum):
    FOUND = "FOUND"
    LOST = "LOST"


class ScanLogCreateRequest(BaseModel):
    item_id: int
    status: ScanStatus


class ScanLogResponse(BaseModel):
    id: int
    user_device_id: int
    item_id: int
    status: ScanStatus
    scanned_at: datetime

    model_config = ConfigDict(from_attributes=True)
