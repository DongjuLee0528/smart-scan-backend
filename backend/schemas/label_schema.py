"""
라벨 관리 API 스키마

Smart Scan 시스템의 라벨 관리 기능을 위한 API 스키마를 정의합니다.
RFID 태그나 아이템에 할당할 수 있는 라벨 번호의 조회와 관리를 지원합니다.

주요 스키마:
- AvailableLabelResponse: 사용 가능한 라벨 번호 목록 응답

데이터 구조:
- 라벨 번호: 정수형 라벨 식별자
- 가용성 정보: 현재 할당되지 않은 라벨 번호들

비즈니스 규칙:
- 라벨 번호는 중복 할당 불가
- 사용 중인 라벨은 가용 목록에서 제외
- 라벨 해제 시 다시 가용 목록에 포함

사용 시나리오:
- 새 RFID 태그 등록 시 사용 가능한 라벨 번호 조회
- 아이템 재할당 시 빈 라벨 번호 확인
- 시스템 관리자의 라벨 현황 파악
"""

from pydantic import BaseModel
from typing import List


class AvailableLabelResponse(BaseModel):
    """
    사용 가능한 라벨 번호 응답 스키마

    현재 할당되지 않은 라벨 번호들의 목록을 반환합니다.
    """
    available_labels: List[int]  # 사용 가능한 라벨 번호 목록