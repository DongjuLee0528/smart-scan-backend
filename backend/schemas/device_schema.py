"""
Device management API schema

Defines API request/response schemas for RFID device registration, modification, and lookup.
Supports data validation and serialization/deserialization using Pydantic.

Main schemas:
- DeviceRegisterRequest: Device registration request (serial number required)
- UserDeviceResponse: Device lookup response (user-device connection info)
- DeviceListResponse: Device list response

Data validation:
- Serial number format validation (empty values, whitespace removal)
- String length limits
- Required field validation

Business rules:
- Serial numbers are unique across the entire system
- Automatic user connection on device registration
- Family-unit device sharing support
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


def _validate_required_text(value: str, field_name: str) -> str:
    normalized_value = value.strip()
    if not normalized_value:
        raise ValueError(f"{field_name} is required")
    return normalized_value


class DeviceRegisterRequest(BaseModel):
    serial_number: str

    @field_validator("serial_number")
    @classmethod
    def validate_serial_number(cls, v: str) -> str:
        return _validate_required_text(v, "serial_number")


class DeviceResponse(BaseModel):
    id: int
    serial_number: str
    family_id: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserDeviceResponse(BaseModel):
    id: int
    user_id: int
    device_id: int
    created_at: datetime
    device: DeviceResponse

    model_config = ConfigDict(from_attributes=True)
