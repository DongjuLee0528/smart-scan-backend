"""
카카오톡 챗봇용 사용자 연결 데이터 리포지토리

카카오톡 사용자와 SmartScan 시스템 간의 연결 정보를 관리하는 데이터베이스 접근 계층입니다.
카카오톡 사용자 ID를 통해 해당 사용자의 디바이스와 가족 구성원 정보에 접근할 수 있도록 연결 테이블을 관리합니다.

주요 기능:
- 카카오 사용자 ID로 연결된 디바이스 및 구성원 정보 조회
- 새로운 카카오 사용자와 SmartScan 계정 연결 생성
- 카카오 사용자 연결 해제 및 정리
- 가족 단위 구성원 조회 (소유자 우선 정렬)

비즈니스 모델:
- kakao_user_id: 카카오톡에서 제공하는 고유 사용자 식별자
- device_id: 해당 사용자가 사용하는 SmartScan RFID 디바이스
- member_id: 가족 내에서의 구성원 정보 (역할 및 권한 포함)

연결 방식:
- 1:1:1 매핑: 한 카카오 사용자는 하나의 디바이스, 하나의 가족 구성원과 연결
- 가족 공유: 같은 가족의 여러 구성원이 하나의 디바이스 공유 가능
- 자동 연결: 디바이스 등록 시 가족 소유자와 자동으로 연결 생성

데이터베이스 스키마:
CREATE TABLE kakao_links (
    kakao_user_id TEXT PRIMARY KEY,
    device_id     BIGINT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    member_id     BIGINT NOT NULL REFERENCES family_members(id) ON DELETE CASCADE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

사용 컨텍스트:
- 카카오톡 챗봇 로그인 및 인증 처리
- 소지품 관리 명령어 실행 시 사용자 식별
- 가족 구성원 권한 확인 및 데이터 접근 제어
"""
from common.db import get_client


def get_user_by_kakao_id(kakao_user_id: str):
    """
    카카오 사용자 ID로 연결 정보 조회

    카카오톡 로그인 시 사용되는 함수로, 사용자의 카카오 ID로
    해당 사용자가 연결된 디바이스와 가족 구성원 정보를 조회합니다.

    Args:
        kakao_user_id: 카카오톡에서 제공하는 고유 사용자 식별자

    Returns:
        dict | None: 연결 정보 또는 None (미등록 사용자)
                     {kakao_user_id, device_id, member_id} 포함

    비즈니스 로직:
        - 등록된 사용자만 카카오톡 명령어 사용 가능
        - device_id로 사용자의 디바이스 접근 권한 확인
        - member_id로 가족 내 역할 및 권한 검증

    사용 예시:
        카카오톡에서 "목록" 명령 시 사용자 인증 및 권한 확인
    """
    res = (get_client()
           .table('kakao_links')
           .select('kakao_user_id, device_id, member_id')
           .eq('kakao_user_id', kakao_user_id)
           .limit(1)
           .execute())
    data = res.data if res else []
    return data[0] if data else None


def create_user_device(kakao_user_id: str, device_id: int, member_id: int):
    """
    새로운 카카오 사용자 연결 생성

    카카오톡 사용자를 SmartScan 시스템의 디바이스 및 가족 구성원과 연결합니다.
    최초 등록 시 또는 관리자가 수동으로 연결을 생성할 때 사용됩니다.

    Args:
        kakao_user_id: 카카오 사용자 ID
        device_id: 연결할 RFID 디바이스 ID
        member_id: 연결할 가족 구성원 ID

    비즈니스 규칙:
        - 한 카카오 사용자는 하나의 연결만 가능
        - device_id와 member_id는 동일한 가족에 속해야 함
        - 연결 생성 시 created_at 자동 설정

    사용 예시:
        디바이스 등록 완료 후 가족 소유자와 카카오톡 연결 생성
    """
    get_client().table('kakao_links').insert({
        'kakao_user_id': kakao_user_id,
        'device_id': device_id,
        'member_id': member_id,
    }).execute()


def delete_user_device(kakao_user_id: str):
    """
    카카오 사용자 연결 해제

    카카오톡 사용자와 SmartScan 시스템 간의 연결을 완전히 삭제합니다.
    사용자가 서비스를 중단하거나 다시 연결할 때 사용됩니다.

    Args:
        kakao_user_id: 연결을 해제할 카카오 사용자 ID

    비즈니스 영향:
        - 해당 사용자는 카카오톡 명령어 사용 불가
        - 재등록 시에는 새로운 연결 생성 필요
        - 가족이나 디바이스 데이터는 영향 없음

    사용 예시:
        사용자가 카카오톡 서비스 사용을 중단하거나 다른 가족에 이동
    """
    get_client().table('kakao_links').delete().eq('kakao_user_id', kakao_user_id).execute()


def get_first_member_by_family(family_id: int):
    """
    가족의 대표 구성원 조회 (소유자 우선)

    지정된 가족의 대표자를 조회하여 자동 연결 생성 시 사용합니다.
    가족 소유자(owner)가 우선적으로 선택되어 관리 권한을 보장합니다.

    Args:
        family_id: 대표 구성원을 찾을 가족 ID

    Returns:
        dict | None: 대표 구성원 정보 또는 None
                     {id, name, role} 포함

    정렬 우선순위:
        1. role='owner' (가족 소유자)
        2. role='member' (일반 구성원)

    비즈니스 컨텍스트:
        - 디바이스 연결 시 기본 연결 대상 선정
        - 관리자 권한이 필요한 작업에 소유자 우선 전달
        - 가족 내 기본 연락처 역할

    사용 예시:
        디바이스 등록 후 가족 소유자와 자동 연결 생성
    """
    res = (get_client()
           .table('family_members')
           .select('id, name, role')
           .eq('family_id', family_id)
           .order('role', desc=True)    # 'owner' > 'member' 내림차순 → owner 우선
           .limit(1)
           .execute())
    return res.data[0] if res.data else None
