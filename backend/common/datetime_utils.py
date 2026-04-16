"""
날짜시간 유틸리티 함수

SmartScan 시스템에서 사용되는 날짜시간 처리를 위한 공통 유틸리티 함수들을 제공합니다.
데이터베이스와 API 간의 타임존 일관성을 보장하기 위해 모든 datetime을 UTC로 정규화합니다.

주요 기능:
- 타임존 정보가 없는 naive datetime을 UTC로 변환
- 타임존 정보가 있는 aware datetime의 UTC 변환
- 옵셔널 datetime과 필수 datetime에 대한 별도 처리

사용 목적:
- JWT 토큰의 만료 시간 정규화
- 데이터베이스 저장 전 datetime 정규화
- API 응답에서 일관된 타임존 제공
- 이메일 인증 만료 시간 검증

타임존 정책:
- 모든 시스템 내부 처리는 UTC 기준
- 클라이언트 표시 시에만 로컬 타임존 적용
- 데이터베이스 저장 시 UTC 강제 적용
"""

from datetime import datetime, timezone


def normalize_datetime(value: datetime | None) -> datetime | None:
    """
    선택적 datetime을 UTC 타임존으로 정규화

    타임존 정보가 없는 naive datetime은 UTC로 가정하여 변환합니다.
    None 값은 그대로 반환하여 옵셔널 필드 처리를 지원합니다.

    Args:
        value: 정규화할 datetime 객체 또는 None

    Returns:
        datetime | None: UTC 타임존이 설정된 datetime 또는 None

    사용 예시:
        API 응답에서 옵셔널 타임스탬프 필드 정규화
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def normalize_datetime_required(value: datetime) -> datetime:
    """
    필수 datetime을 UTC 타임존으로 정규화

    타임존 정보가 없는 naive datetime은 UTC로 가정하여 변환합니다.
    None 값이 전달되면 타입 에러가 발생하므로 필수 필드에만 사용해야 합니다.

    Args:
        value: 정규화할 datetime 객체 (필수)

    Returns:
        datetime: UTC 타임존이 설정된 datetime

    Raises:
        AttributeError: value가 None인 경우

    사용 예시:
        JWT 토큰 만료 시간, 데이터베이스 저장 시간 정규화
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value