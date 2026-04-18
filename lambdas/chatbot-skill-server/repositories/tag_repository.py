"""
카카오톡 챗봇용 태그 및 디바이스 데이터 리포지토리

카카오톡 챗봇에서 RFID 태그와 디바이스 정보를 조회하기 위한 데이터베이스 접근 계층입니다.
물리적 RFID 태그의 연결 상태와 사용 가능한 라벨 슬롯을 관리하는 기능을 제공합니다.

주요 기능:
- 시리얼 번호로 디바이스 조회 (디바이스 인증용)
- 라벨과 디바이스 조합으로 태그 조회
- 디바이스의 사용 가능한 라벨 슬롯 확인

비즈니스 컨텍스트:
- 카카오톡 챗봇에서 디바이스 연결 상태 확인
- 새로운 소지품 추가 시 사용 가능한 라벨 검증
- RFID 태그와 소지품의 물리적 연결 관리

데이터 구조:
- devices: 물리적 RFID 리더기 정보
- tags: 디바이스에 연결된 물리적 RFID 태그
- label: 태그의 물리적 위치 식별자 (1~N번 슬롯)

사용 시나리오:
- 사용자가 카카오톡에서 소지품 추가 시 라벨 확인
- 디바이스 등록 및 연결 상태 검증
- 물리적 태그 슬롯의 사용 가능 여부 조회
"""

from common.db import get_client


def get_device_by_serial(serial_number: str):
    """
    시리얼 번호로 디바이스 조회

    카카오톡 챗봇 인증에 사용되는 함수로, 사용자가 제공한
    디바이스 시리얼 번호로 등록된 디바이스 정보를 조회합니다.

    Args:
        serial_number: RFID 리더기의 고유 시리얼 번호

    Returns:
        dict | None: 디바이스 정보 또는 None
                     {id, family_id, serial_number, name} 포함

    비즈니스 로직:
        - 활성 상태(is_active=True)인 디바이스만 조회
        - 가족 ID로 사용자 권한 검증 준비
        - 디바이스 인증 및 연결 상태 확인용

    사용 예시:
        카카오톡 챗봇 로그인 시 디바이스 소유권 검증
    """
    res = (get_client()
           .table('devices')
           .select('id, family_id, serial_number, name')
           .eq('serial_number', serial_number)
           .eq('is_active', True)
           .maybe_single()
           .execute())
    return res.data


def get_tag_by_label(device_id: int, label: str):
    """
    디바이스 ID와 라벨로 태그 조회

    특정 디바이스의 지정된 라벨 슬롯에 연결된 물리적 RFID 태그 정보를 조회합니다.
    소지품 추가/수정 시 해당 라벨의 태그 사용 가능 여부를 확인하는 데 사용됩니다.

    Args:
        device_id: RFID 리더기 디바이스 ID
        label: 물리적 태그 슬롯 번호 (1, 2, 3, ... N번)

    Returns:
        dict | None: 태그 정보 또는 None
                     {id, tag_uid, item_id, label} 포함

    데이터 구조:
        - tag_uid: 물리적 RFID 태그의 고유 식별자
        - item_id: 연결된 소지품 ID (NULL이면 미사용 슬롯)
        - label: 물리적 슬롯 위치 식별자

    사용 예시:
        사용자가 "추가 지갑 3" 명령 시 3번 라벨 사용 가능 여부 확인
    """
    res = (get_client()
           .table('tags')
           .select('id, tag_uid, item_id, label')
           .eq('device_id', device_id)
           .eq('label', label)
           .eq('is_active', True)
           .maybe_single()
           .execute())
    return res.data


def get_available_labels(device_id: int) -> list:
    """
    디바이스에서 사용 가능한 라벨 슬롯 목록 조회

    지정된 디바이스에서 현재 등록된 모든 태그의 라벨 목록을 반환합니다.
    카카오톡 챗봇에서 소지품 추가 시 사용 가능한 라벨을 안내하는 데 사용됩니다.

    Args:
        device_id: RFID 리더기 디바이스 ID

    Returns:
        list: 등록된 태그의 라벨 목록 ([문자열] 형태)

    비즈니스 로직:
        - 활성 상태의 태그만 조회
        - item_id가 NULL인 태그는 없다고 가정
        - 웹에서 미사용 슬롯 관리 수행

    사용 예시:
        사용자가 "추가" 명령 시 사용 가능한 라벨 안내
        "현재 1, 2, 3번 라벨에 소지품이 등록되어 있습니다"
    """
    res = (get_client()
           .table('tags')
           .select('label, item_id')
           .eq('device_id', device_id)
           .eq('is_active', True)
           .execute())
    tags = res.data or []
    # item_id가 NULL인 태그는 없으므로, 태그가 없는 슬롯은 웹에서 관리
    return [t['label'] for t in tags if t.get('label')]
