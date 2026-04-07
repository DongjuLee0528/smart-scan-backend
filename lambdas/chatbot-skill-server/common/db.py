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
