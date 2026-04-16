"""
외출 알림 Lambda용 Supabase 데이터베이스 클라이언트 관리

사용자의 외출 상태 변화를 감지하고 알림을 발송하기 위한 데이터베이스 연결을 관리하는 유틸리티입니다.
RFID 스캔 이벤트 처리 후 이메일/SMS 알림 발송에 필요한 사용자 및 가족 정보 조회를 지원합니다.

주요 기능:
- Supabase 클라이언트 싱글톤 관리 및 연결 최적화
- 외출 알림 발송을 위한 안전한 데이터베이스 접근
- Lambda 환경에서의 효율적인 리소스 관리

사용 컨텍스트:
- 외출/귀가 상태 변화 감지 시 사용자 정보 조회
- 가족 구성원 알림 설정 확인
- 알림 발송 이력 저장 및 관리
- 사용자 선호 설정 및 연락처 정보 조회

보안 및 성능:
- SUPABASE_SERVICE_KEY를 사용한 백엔드 전용 접근
- LRU 캐시를 통한 연결 재사용으로 Lambda 성능 최적화
- 환경변수를 통한 안전한 인증 정보 관리

알림 시나리오:
- 가족 구성원의 외출 시작 알림
- 예상 귀가 시간 초과 알림
- 긴급 상황 또는 비정상적인 패턴 감지 알림
"""

import os
from functools import lru_cache
from supabase import create_client, Client


@lru_cache(maxsize=1)
def get_client() -> Client:
    """
    외출 알림 전용 Supabase 클라이언트 인스턴스 반환

    외출 알림 Lambda에서 사용자 정보 및 알림 설정 조회를 위한
    데이터베이스 클라이언트를 생성하고 캐시된 인스턴스를 반환합니다.

    Returns:
        Client: Supabase 클라이언트 인스턴스 (알림 발송용)

    Raises:
        ValueError: 필수 환경변수가 설정되지 않은 경우

    환경변수:
        SUPABASE_URL: Supabase 프로젝트 URL
        SUPABASE_SERVICE_KEY: 백엔드 전용 서비스 키

    사용 목적:
        - 외출/귀가 이벤트 발생 시 사용자 정보 조회
        - 가족 구성원 알림 설정 확인 및 연락처 정보 조회
        - 알림 발송 이력 저장 및 통계 데이터 수집
    """
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_SERVICE_KEY')
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    return create_client(url, key)
