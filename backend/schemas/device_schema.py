"""
디바이스 관리 API 스키마

RFID 디바이스 등록, 수정, 조회를 위한 API 요청/응답 스키마를 정의합니다.
Pydantic을 사용하여 데이터 검증과 직렬화/역직렬화를 지원합니다.

주요 스키마:
- DeviceRegisterRequest: 디바이스 등록 요청 (시리얼 번호 필수)
- UserDeviceResponse: 디바이스 조회 응답 (사용자-디바이스 연결 정보)
- DeviceListResponse: 디바이스 목록 응답

데이터 검증:
- 시리얼 번호 형식 검증 (빈 값, 공백 제거)
- 문자열 길이 제한
- 필수 필드 유효성 검사

비즈니스 규칙:
- 시리얼 번호는 전체 시스템에서 고유
- 디바이스 등록 시 사용자와 자동 연결
- 가족 단위 디바이스 공유 지원
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
