"""
스캔 로그 API 스키마

Smart Scan 시스템의 RFID 스캔 기록을 위한 API 스키마를 정의합니다.
디바이스에서 감지된 아이템의 발견/분실 상태를 추적하고 기록합니다.

주요 스키마:
- ScanStatus: 스캔 상태 (발견됨, 분실됨)
- ScanLogCreateRequest: 스캔 로그 생성 요청
- ScanLogResponse: 스캔 로그 상세 정보 응답

데이터 구조:
- 스캔 상태: RFID 태그의 현재 감지 상태
- 아이템 정보: 스캔된 아이템의 식별자
- 시간 정보: 스캔이 발생한 정확한 시각
- 디바이스 정보: 스캔을 수행한 사용자-디바이스 조합

비즈니스 규칙:
- 스캔 로그는 실시간으로 생성
- 연속된 같은 상태 스캔은 중복 제거 가능
- 분실 상태는 일정 시간 후 자동 생성
- 스캔 이력은 아이템 추적의 핵심 데이터

사용 시나리오:
- RFID 디바이스에서 태그 감지 시 로그 생성
- 아이템 분실 감지 및 알림 트리거
- 사용자의 소지품 이동 경로 추적
- 가족 구성원의 아이템 사용 패턴 분석
"""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict


class ScanStatus(str, Enum):
    """
    스캔 상태 열거형

    RFID 태그의 현재 감지 상태를 나타냅니다.
    """
    FOUND = "FOUND"  # 발견됨 - 태그가 RFID 리더기에 감지됨
    LOST = "LOST"  # 분실됨 - 태그가 일정 시간 감지되지 않음


class ScanLogCreateRequest(BaseModel):
    """
    스캔 로그 생성 요청 스키마

    RFID 디바이스에서 태그 스캔 결과를 서버에 전송할 때 사용됩니다.
    """
    item_id: int  # 스캔된 아이템 ID
    status: ScanStatus  # 스캔 상태 (발견/분실)


class ScanLogResponse(BaseModel):
    """
    스캔 로그 상세 정보 응답 스키마

    스캔 로그의 모든 정보를 클라이언트에 전달합니다.
    """
    id: int  # 스캔 로그 고유 ID
    user_device_id: int  # 사용자-디바이스 연결 ID
    item_id: int  # 스캔된 아이템 ID
    status: ScanStatus  # 스캔 상태
    scanned_at: datetime  # 스캔 발생 시간

    model_config = ConfigDict(from_attributes=True)
