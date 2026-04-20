"""
가상 태그 관리 API 스키마

사용자가 생성하는 가상 태그의 생성, 수정, 조회를 위한 API 스키마를 정의합니다.
실제 물리적 RFID 태그와 연결되기 전 단계의 논리적 태그 데이터 구조를 제공합니다.

주요 스키마:
- CreateTagRequest: 새로운 가상 태그 생성 요청
- UpdateTagRequest: 기존 태그 정보 수정 요청
- TagResponse: 태그 상세 정보 응답
- TagListResponse: 태그 목록 응답

데이터 구조:
- 태그 고유 식별자 (tag_uid)
- 태그 이름 (사용자 정의)
- 소유자 및 연결 디바이스 정보
- 활성 상태 (삭제 시 비활성화)

비즈니스 규칙:
- 태그는 반드시 특정 디바이스에 연결
- 태그 UID는 전체 시스템에서 고유
- 가족 구성원만 해당 가족의 태그 조회 가능
- 소유자만 태그 수정/삭제 가능
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
