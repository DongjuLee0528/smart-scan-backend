"""
가족 초대 Pydantic 스키마

요청/응답 직렬화 및 입력 검증을 위한 스키마를 정의합니다.

제공 스키마:
- CreateInvitationRequest: 초대 생성 요청 본문
- InvitationResponse: 단일 초대 응답 (민감정보 최소화)
- InvitationListResponse: 초대 목록 응답
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


class CreateInvitationRequest(BaseModel):
    """
    초대 생성 요청 본문

    가족 소유자가 이메일로 새 구성원을 초대할 때 사용한다.
    name, phone_number는 초대 메일 본문에 표시되는 참고용 정보이며
    실제 가입 정보는 수락 시 current_user 기준으로 처리된다.
    """
    name: str
    email: str
    phone_number: str
    age: Optional[int] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name은 필수입니다")
        return v

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        v = v.strip()
        if not v or "@" not in v:
            raise ValueError("email 형식이 올바르지 않습니다")
        return v

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("phone_number는 필수입니다")
        return v

    @field_validator("age")
    @classmethod
    def validate_age(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 0 or v > 150):
            raise ValueError("age는 0~150 사이여야 합니다")
        return v


class InvitationResponse(BaseModel):
    """
    단일 초대 응답

    by-token 공개 조회와 오너 목록 조회 모두에서 동일 형식을 사용한다.
    수신자 이메일과 상태, 가족/초대자 이름만 노출하여 민감정보를 최소화한다.
    """
    id: int
    family_id: int
    family_name: str
    inviter_name: str
    email: str
    status: str
    expires_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class InvitationListResponse(BaseModel):
    """
    가족 pending 초대 목록 응답
    """
    invitations: list[InvitationResponse]
    total_count: int


class AcceptInvitationResponse(BaseModel):
    """
    초대 수락 성공 응답 — 이동한 가족 정보 반환
    """
    family_id: int
    family_name: str
    role: str


class DeclineInvitationResponse(BaseModel):
    """
    초대 거절 성공 응답
    """
    status: str
