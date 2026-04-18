"""
모니터링 대시보드 API 스키마

Smart Scan 시스템의 모니터링 대시보드에서 사용되는 API 스키마를 정의합니다.
가족 구성원별 태그 상태, 전체 현황, 개별 태그 추적 정보를 체계적으로 관리합니다.

주요 스키마:
- TagCurrentStatus: 태그의 현재 상태 (등록됨, 발견됨, 분실됨)
- MemberSummaryResponse: 가족 구성원별 태그 현황 요약
- TagStatusResponse: 개별 태그의 상세 상태 정보
- MonitoringDashboardResponse: 전체 가족 모니터링 대시보드
- MemberTagStatusListResponse: 특정 구성원의 태그 목록
- MyTagStatusListResponse: 본인의 태그 목록

데이터 구조:
- 태그 상태: 등록, 발견, 분실 상태 추적
- 소유권 정보: 태그별 소유자 및 담당자 관리
- 시간 추적: 마지막 발견, 스캔 시간 기록
- 통계 정보: 구성원별, 상태별 집계 데이터

비즈니스 규칙:
- 가족 구성원은 서로의 태그 상태 조회 가능
- 태그 상태는 실시간 업데이트
- 분실된 태그는 알림 시스템과 연동
- 통계 데이터는 캐싱으로 성능 최적화

사용 시나리오:
- 가족 전체 태그 현황 대시보드 조회
- 특정 구성원의 소지품 상태 확인
- 분실된 아이템 빠른 식별 및 알림
- 가족 내 소지품 관리 현황 파악
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class TagCurrentStatus(str, Enum):
    """
    태그 현재 상태 열거형

    RFID 태그의 현재 추적 상태를 나타냅니다.
    """
    REGISTERED = "REGISTERED"  # 등록됨 - 태그가 등록되었지만 아직 스캔되지 않음
    FOUND = "FOUND"  # 발견됨 - 태그가 최근에 스캔되어 위치 확인됨
    LOST = "LOST"  # 분실됨 - 태그가 일정 시간 스캔되지 않아 분실로 판단됨


class MemberSummaryResponse(BaseModel):
    """
    가족 구성원 태그 현황 요약 응답 스키마

    대시보드에서 각 구성원별 태그 상태 통계를 표시하는 데 사용됩니다.
    """
    member_id: int  # 가족 구성원 ID
    user_id: int  # 연결된 사용자 ID
    name: Optional[str] = None  # 구성원 이름
    email: Optional[str] = None  # 구성원 이메일
    role: str  # 가족 내 역할 (owner, member)
    tag_count: int  # 총 태그 수
    found_count: int  # 발견된 태그 수
    lost_count: int  # 분실된 태그 수
    registered_count: int  # 등록된 태그 수


class TagStatusResponse(BaseModel):
    """
    개별 태그 상태 상세 응답 스키마

    태그의 현재 상태, 소유자, 연결된 아이템 정보를 포함합니다.
    """
    tag_id: int  # 태그 ID
    tag_uid: str  # RFID 태그 고유 식별자
    name: str  # 태그 이름
    owner_user_id: int  # 태그 소유자 사용자 ID
    owner_member_id: Optional[int] = None  # 태그 소유자 구성원 ID
    owner_name: Optional[str] = None  # 태그 소유자 이름
    status: TagCurrentStatus  # 현재 태그 상태
    is_active: bool  # 태그 활성 여부
    item_id: Optional[int] = None  # 연결된 아이템 ID
    item_name: Optional[str] = None  # 연결된 아이템 이름
    device_id: Optional[int] = None  # 마지막 스캔된 디바이스 ID
    last_seen_at: Optional[datetime] = None  # 마지막 발견 시간
    last_scanned_at: Optional[datetime] = None  # 마지막 스캔 시간
    created_at: datetime  # 태그 등록 시간
    updated_at: datetime  # 태그 정보 업데이트 시간


class DashboardSummaryResponse(BaseModel):
    """
    대시보드 전체 요약 응답 스키마

    가족 전체의 태그 현황을 한 눈에 볼 수 있는 요약 정보를 제공합니다.
    """
    total_members: int  # 총 가족 구성원 수
    total_tags: int  # 총 등록된 태그 수
    found_count: int  # 발견된 태그 수
    lost_count: int  # 분실된 태그 수
    registered_count: int  # 새로 등록된 태그 수


class MonitoringDashboardResponse(BaseModel):
    """
    모니터링 대시보드 메인 응답 스키마

    가족 전체의 모니터링 현황을 종합적으로 제공하는 대시보드 데이터입니다.
    """
    family_id: int  # 가족 ID
    family_name: str  # 가족 이름
    requester_member_id: int  # 요청자 구성원 ID
    requester_role: str  # 요청자 역할
    summary: DashboardSummaryResponse  # 전체 요약 정보
    members: list[MemberSummaryResponse]  # 구성원별 요약 정보 목록


class MemberTagStatusListResponse(BaseModel):
    """
    특정 구성원의 태그 상태 목록 응답 스키마

    가족의 특정 구성원이 소유한 모든 태그의 상태를 조회할 때 사용됩니다.
    """
    family_id: int  # 가족 ID
    family_name: str  # 가족 이름
    member_id: int  # 조회 대상 구성원 ID
    user_id: int  # 조회 대상 사용자 ID
    member_name: Optional[str] = None  # 구성원 이름
    role: str  # 구성원 역할
    tags: list[TagStatusResponse]  # 태그 상태 목록
    total_count: int  # 총 태그 수


class MyTagStatusListResponse(BaseModel):
    """
    본인의 태그 상태 목록 응답 스키마

    로그인한 사용자 본인의 태그 목록을 조회할 때 사용됩니다.
    """
    family_id: int  # 가족 ID
    family_name: str  # 가족 이름
    member_id: int  # 본인의 구성원 ID
    tags: list[TagStatusResponse]  # 본인의 태그 상태 목록
    total_count: int  # 총 태그 수
