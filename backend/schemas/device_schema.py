from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator


class DeviceRegisterRequest(BaseModel):
    kakao_user_id: str
    serial_number: str

    @field_validator("kakao_user_id")
    @classmethod
    def validate_kakao_user_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("kakao_user_id is required")
        return v.strip()

    @field_validator("serial_number")
    @classmethod
    def validate_serial_number(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("serial_number is required")
        return v.strip()


class DeviceResponse(BaseModel):
    id: int
    serial_number: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserDeviceResponse(BaseModel):
    id: int
    user_id: int
    device_id: int
    created_at: datetime
    device: DeviceResponse

    model_config = ConfigDict(from_attributes=True)


class DeviceUnlinkRequest(BaseModel):
    kakao_user_id: str

    @field_validator("kakao_user_id")
    @classmethod
    def validate_kakao_user_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("kakao_user_id is required")
        return v.strip()
