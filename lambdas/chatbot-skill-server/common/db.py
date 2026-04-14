"""
Supabase 데이터베이스 클라이언트 (카카오 챗봇용)

카카오 챗봇 Lambda 함수에서 Supabase PostgreSQL에 연결하기 위한 클라이언트를 제공합니다.
LRU 캐싱을 이용하여 Lambda 콜드 스타트 시간을 최소화합니다.

환경변수:
- SUPABASE_URL: Supabase 프로젝트 URL
- SUPABASE_SERVICE_KEY: 서비스 롤 키 (전체 데이터베이스 접근 권한)

사용 예: get_client().table('users').select('*').execute()
"""

import os
from functools import lru_cache
from supabase import create_client, Client


@lru_cache(maxsize=1)
def get_client() -> Client:
    # 환경변수: SUPABASE_URL, SUPABASE_SERVICE_KEY
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_SERVICE_KEY')
    if not url:
        raise ValueError("환경변수 SUPABASE_URL이 설정되지 않았습니다.")
    if not key:
        raise ValueError("환경변수 SUPABASE_SERVICE_KEY가 설정되지 않았습니다.")
    return create_client(url, key)
