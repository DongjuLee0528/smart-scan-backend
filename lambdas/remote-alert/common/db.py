"""
원격 알림 Lambda용 Supabase 데이터베이스 클라이언트 관리

원격지에서의 긴급 상황이나 특별한 이벤트 발생 시 즉시 알림을 발송하기 위한 데이터베이스 연결을 관리합니다.
사용자의 위치와 관계없이 중요한 알림을 안정적으로 전달할 수 있도록 데이터베이스 접근을 지원합니다.

주요 기능:
- Supabase 클라이언트 싱글톤 관리 및 안정적인 연결 보장
- 긴급 알림 발송을 위한 고속 데이터베이스 접근
- 한국어 에러 메시지를 통한 개발자 친화적 오류 처리

사용 컨텍스트:
- 긴급 상황 감지 시 즉시 알림 발송
- 보안 이벤트 또는 침입 감지 알림
- 시스템 장애나 중요한 상태 변화 통지
- 원격 모니터링 및 관리 알림

특별 기능:
- 한국어 에러 메시지로 로컬 개발 환경 지원
- 환경변수 검증을 통한 안전한 배포 보장
- Lambda Cold Start 최적화를 위한 연결 캐싱

알림 시나리오:
- 침입자 감지나 보안 위협 상황
- 시스템 임계값 초과나 장애 발생
- 사용자 정의 규칙에 따른 특별한 이벤트 발생
- 원격 관리가 필요한 상황 발생
"""

import os
from functools import lru_cache
from supabase import create_client, Client


@lru_cache(maxsize=1)
def get_client() -> Client:
    """
    원격 알림 전용 Supabase 클라이언트 인스턴스 반환

    원격 알림 Lambda에서 긴급 상황이나 중요 이벤트 발생 시
    즉시 알림 발송을 위한 데이터베이스 클라이언트를 생성하고 반환합니다.

    안정적인 알림 전송을 위해 환경변수 검증과 한국어 에러 메시지를 제공합니다.

    Returns:
        Client: Supabase 클라이언트 인스턴스 (원격 알림용)

    Raises:
        ValueError: 필수 환경변수가 설정되지 않은 경우 (한국어 메시지)

    환경변수:
        SUPABASE_URL: Supabase 프로젝트 URL
        SUPABASE_SERVICE_KEY: 백엔드 전용 서비스 키

    사용 목적:
        - 긴급 상황 감지 시 사용자 및 관리자 정보 조회
        - 알림 발송 설정 및 연락처 정보 확인
        - 원격 알림 발송 이력 저장 및 추적
        - 시스템 상태 모니터링 및 장애 대응
    """
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_SERVICE_KEY')
    if not url:
        raise ValueError("환경변수 SUPABASE_URL이 설정되지 않았습니다.")
    if not key:
        raise ValueError("환경변수 SUPABASE_SERVICE_KEY가 설정되지 않았습니다.")
    return create_client(url, key)
