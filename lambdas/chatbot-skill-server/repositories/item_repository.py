"""
카카오톡 챗봇용 아이템 데이터 리포지토리

카카오톡 챗봇에서 소지품(아이템) 관리를 위한 데이터베이스 접근 계층입니다.
사용자가 챗봇을 통해 소지품을 조회, 추가, 삭제할 때 사용되는 간단한 CRUD 연산을 제공합니다.

주요 기능:
- 활성 소지품 목록 조회 (필수 아이템 여부 포함)
- 새로운 소지품 추가 (기본값: 필수 아이템으로 등록)
- 소지품 비활성화 (소프트 삭제)
- 가족 구성원의 모든 소지품 일괄 비활성화

비즈니스 규칙:
- 모든 소지품은 기본적으로 필수 아이템(is_required=True)으로 등록
- 삭제는 비활성화(is_active=False)를 통한 소프트 삭제
- member_id를 통한 가족 구성원별 소지품 관리
- 카카오톡 챗봇 환경에 최적화된 간소화된 인터페이스

사용 컨텍스트:
- 카카오톡에서 "목록", "추가", "삭제" 명령어 처리
- 소지품 관리 대화형 인터페이스 지원
- 메인 백엔드 시스템과의 데이터 동기화 유지
"""

from common.db import get_client


def get_active_items(member_id: int) -> list:
    """
    가족 구성원의 활성 소지품 목록 조회

    카카오톡에서 "목록" 명령어 실행 시 호출되는 함수입니다.
    해당 구성원이 등록한 모든 활성 소지품의 이름과 필수 여부를 반환합니다.

    Args:
        member_id: 가족 구성원 ID

    Returns:
        list: 소지품 정보 리스트 (id, name, is_required 포함)
              생성일자 순으로 정렬되어 반환

    사용 예시:
        카카오톡에서 현재 등록된 소지품 목록을 확인할 때
    """
    res = (get_client()
           .table('items')
           .select('id, name, is_required')
           .eq('member_id', member_id)
           .eq('is_active', True)
           .order('created_at')
           .execute())
    return res.data or []


def add_item(name: str, member_id: int) -> dict:
    """
    새로운 소지품 등록

    카카오톡에서 "추가 [아이템명]" 명령어 실행 시 호출되는 함수입니다.
    새로운 소지품을 필수 아이템으로 등록하고 활성 상태로 설정합니다.

    Args:
        name: 등록할 소지품 이름
        member_id: 소지품을 등록하는 가족 구성원 ID

    Returns:
        dict | None: 생성된 소지품 정보 또는 실패 시 None

    기본 설정:
        - is_required: True (필수 소지품으로 등록)
        - is_active: True (활성 상태)
    """
    res = (get_client()
           .table('items')
           .insert({'name': name, 'member_id': member_id, 'is_required': True, 'is_active': True})
           .execute())
    return res.data[0] if res.data else None


def deactivate_item(name: str, member_id: int) -> int:
    """
    특정 소지품 비활성화 (소프트 삭제)

    카카오톡에서 "삭제 [아이템명]" 명령어 실행 시 호출되는 함수입니다.
    지정된 이름의 소지품을 비활성화하여 목록에서 제외합니다.

    Args:
        name: 삭제할 소지품 이름
        member_id: 가족 구성원 ID

    Returns:
        int: 비활성화된 소지품 수 (성공 시 1, 실패 시 0)
    """
    res = (get_client()
           .table('items')
           .update({'is_active': False})
           .eq('member_id', member_id)
           .eq('name', name)
           .eq('is_active', True)
           .execute())
    return len(res.data) if res.data else 0


def delete_all_items(member_id: int):
    """
    가족 구성원의 모든 소지품 일괄 비활성화

    카카오톡에서 "기기 해제" 명령어 실행 시 호출되는 함수입니다.
    해당 구성원이 등록한 모든 활성 소지품을 한 번에 비활성화합니다.

    Args:
        member_id: 가족 구성원 ID

    사용 컨텍스트:
        디바이스 해제 시 관련된 모든 소지품 데이터 정리
    """
    get_client().table('items').update({'is_active': False}).eq('member_id', member_id).eq('is_active', True).execute()
