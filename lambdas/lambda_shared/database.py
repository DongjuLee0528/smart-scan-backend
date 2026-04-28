"""
Supabase 데이터베이스 클라이언트 관리

RFID 스캔 데이터 처리를 위한 Supabase 데이터베이스 연결을 관리하는 유틸리티입니다.
Lambda 함수에서 효율적인 데이터베이스 접근을 위해 연결 풀링과 캐싱을 지원합니다.

주요 기능:
- Supabase 클라이언트 싱글톤 관리
- 환경변수를 통한 보안 인증 정보 관리
- LRU 캐시를 통한 연결 재사용으로 성능 최적화

보안 설정:
- SUPABASE_SERVICE_KEY: 백엔드 전용 서비스 키 사용
- 환경변수를 통한 민감 정보 보호
- Lambda 실행 환경에서의 안전한 DB 접근

사용 컨텍스트:
- RFID 스캔 데이터 실시간 저장
- 소지품 상태 변경 로그 기록
- 사용자 디바이스 정보 조회
- 스캔 이벤트 알림 처리

성능 최적화:
- 단일 클라이언트 인스턴스 재사용
- Lambda Cold Start 시간 단축
- 연결 풀링을 통한 응답 시간 개선
"""

import os
from functools import lru_cache
from supabase import create_client, Client


@lru_cache(maxsize=1)
def get_client() -> Client:
    """
    Supabase 클라이언트 싱글톤 인스턴스 반환

    Lambda 함수에서 효율적인 데이터베이스 접근을 위해
    LRU 캐시를 사용하여 클라이언트 인스턴스를 재사용합니다.

    Returns:
        Client: Supabase 클라이언트 인스턴스

    Raises:
        ValueError: 필수 환경변수가 설정되지 않은 경우

    환경변수:
        SUPABASE_URL: Supabase 프로젝트 URL
        SUPABASE_SERVICE_KEY: 백엔드 전용 서비스 키

    사용 예시:
        RFID 스캔 데이터를 데이터베이스에 저장할 때 호출
    """
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_SERVICE_KEY')
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    return create_client(url, key)