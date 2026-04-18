"""
소지품(아이템) 관리 API 스키마

RFID 태그와 연결되는 실제 소지품의 생성, 수정, 조회를 위한 API 스키마를 정의합니다.
사용자의 소지품 등록과 관리를 위한 데이터 구조를 제공합니다.

주요 스키마:
- ItemAddRequest: 새로운 소지품 등록 요청
- ItemUpdateRequest: 기존 소지품 정보 수정 요청
- ItemResponse: 소지품 상세 정보 응답
- ItemListResponse: 소지품 목록 응답

데이터 구조:
- 소지품 이름 (필수)
- 라벨 ID (카테고리 분류용)
- 태그 연결 정보
- 상태 정보 (활성/비활성)

비즈니스 규칙:
- 소지품은 반드시 물리적 RFID 태그와 1:1 연결
- 라벨을 통한 카테고리 분류 지원
- 가족 구성원은 모든 소지품 조회 가능
- 소지품 삭제 시 연관 태그 및 스캔 로그 연쇄 삭제
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


class ItemResponse(BaseModel):
    id: int
    name: str
    label_id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ItemListResponse(BaseModel):
    items: list[ItemResponse]
    total_count: int
