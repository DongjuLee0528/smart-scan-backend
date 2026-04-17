"""
가족 구성원 관리 API 스키마

Smart Scan 시스템의 가족 구성원 추가, 조회, 관리를 위한 API 스키마를 정의합니다.
가족 소유자가 새로운 구성원을 초대하고 관리할 수 있는 기능을 지원합니다.

주요 스키마:
- AddFamilyMemberRequest: 새로운 가족 구성원 초대 요청
- FamilyMemberResponse: 가족 구성원 상세 정보 응답
- FamilyMemberListResponse: 가족 구성원 목록 및 가족 정보 응답

데이터 구조:
- 기본 정보: 이름, 이메일, 전화번호, 나이 (선택)
- 가족 내 역할: owner(소유자), member(일반 구성원)
- 연결 정보: 사용자 계정과의 매핑

비즈니스 규칙:
- 가족 소유자만 새 구성원 초대 가능
- 초대된 구성원은 별도 계정 생성 후 연결
- 구성원 정보는 가족 내에서만 공유
- 개인정보 보호를 위한 선택적 정보 제공

사용 시나리오:
- 가족 소유자가 배우자나 자녀를 시스템에 초대
- 가족 구성원 목록 조회 및 연락처 관리
- 구성원별 역할 및 권한 관리
- 가족 단위 소지품 공유 설정
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


def _validate_required_text(value: str, field_name: str) -> str:
    normalized_value = value.strip()
    if not normalized_value:
        raise ValueError(f"{field_name} is required")
    return normalized_value


class AddFamilyMemberRequest(BaseModel):
    name: str
    email: str
    phone_number: str
    age: Optional[int] = None

    @field_validator("name", "email", "phone_number")
    @classmethod
    def validate_required_text(cls, v: str, info) -> str:
        return _validate_required_text(v, info.field_name)


class FamilyMemberResponse(BaseModel):
    id: int
    family_id: int
    user_id: int
    role: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    age: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FamilyMemberListResponse(BaseModel):
    family_id: int
    family_name: str
    members: list[FamilyMemberResponse]
    total_count: int
